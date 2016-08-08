#!/bin/bash -ex

usage() {
    echo "Usage: $0 [-v <midonet version to upgrade to>]"
    echo "          [-a <old api port>]"
    echo "          [-n <new api port>]"
    echo "          [-h <api host>]"
    echo "          [-m <midonet uri>]"
    echo "          [-u <midonet uri>]"
    echo "          [-d <db connection string>]"
    echo "          [-r <project id>]"
    echo "          [-p <password>]"
    echo "          [-u <username>]"
    echo "          [-z <list of zk servers, comma separated, no space>]" exit 1
}

while getopts "v:a:n:h:m:u:d:r:p:u:z:PEA" o; do
    case "${o}" in
        v)
            VERSION=$OPTARG
            ;;
        a)
            OLD_API_PORT=$OPTARG
            ;;
        n)
            NEW_API_PORT=$OPTARG
            ;;
        h)
            API_HOST=$OPTARG
            ;;
        m)
            OLD_MIDONET_URI=$OPTARG
            ;;
        u)
            NEW_MIDONET_URI=$OPTARG
            ;;
        d)
            DB_CONN=$OPTARG
            ;;
        r)
            PROJECT_ID=$OPTARG
            ;;
        p)
            PASSWORD=$OPTARG
            ;;
        u)
            USERNAME=$OPTARG
            ;;
        z)
            ZK_SERVERS=$OPTARG
            ;;
        P)
            PR2ER=TRUE
            ;;
        E)
            EXTRAROUTES=TRUE
            ;;
        A)
            ANTISPOOF=TRUE
            ;;
        *)
            usage
            ;;
    esac
done

VERSION=${VERSION:-5.2}
OLD_API_PORT=${OLD_API_PORT:-8080}
NEW_API_PORT=${NEW_API_PORT:-8181}
API_HOST=${API_HOST:-localhost}
OLD_MIDONET_URI=${OLD_MIDONET_URI:-http://$API_HOST:$OLD_API_PORT/midonet-api}
NEW_MIDONET_URI=${NEW_MIDONET_URI:-http://$API_HOST:$NEW_API_PORT/midonet-api}

DB_CONN=${DB_CONN:-mysql://neutron:cat@localhost/neutron}
PROJECT_ID=${PROJECT_ID:-admin}
PASSWORD=${PASSWORD:-cat}
USERNAME=${USERNAME:-admin}

ZK_SERVERS=${ZK_SERVERS:-127.0.0.1:2181}

PR2ER=${PR2ER:-FALSE}
EXTRAROUTES=${EXTRAROUTES:-FALSE}
ANTISPOOF=${ANTISPOOF:-FALSE}

# clone the data-migration project to get its scripts
rm -rf run_dm
git clone http://github.com/midonet/data-migration run_dm
cd run_dm

# Create the config files to be used
cat > mig.conf <<EOL
[database]
connection = $DB_CONN
[MIDONET]
project_id = $PROJECT_ID
password = $PASSWORD
username = $USERNAME
midonet_uri = $OLD_MIDONET_URI
[zookeeper]
servers = $ZK_SERVERS
EOL

cat > ~/.midonetrc <<EOL
[cli]
project_id=$PROJECT_ID
password=$PASSWORD
username=$USERNAME
api_url=$OLD_MIDONET_URI
EOL

# Save all of the current data
./migrate.py -c mig.conf prepare > data_prep.json 2> prepare.log

# stop the Midonet Api
sudo service tomcat7 stop

sudo cp /etc/apt/sources.list.d/midonet.list .

# Install the new packages
sudo cat > /etc/apt/sources.list.d/midonet.list <<EOL
deb http://builds.midonet.org/midonet-$VERSION stable main
deb http://builds.midonet.org/misc stable main
EOL

curl -L https://builds.midonet.org/midorepo.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y midonet-cluster python-midonetclient midonet-tools midolman


export MIDO_ZOOKEEPER_HOSTS=$ZK_SERVERS
mn-conf set "cluster.rest_api.http_port=$NEW_API_PORT"
mn-conf set "cluster.neutron_importer.enabled=false"
mn-conf set "cluster.loggers.root=DEBUG"
mn-conf set "agent.loggers.root=DEBUG"

sudo service midonet-cluster restart

cat > mig.conf <<EOL
[database]
connection = $DB_CONN
[MIDONET]
client = midonet.neutron.client.api.MidonetApiClient
project_id = $PROJECT_ID
password = $PASSWORD
username = $USERNAME
midonet_uri = $NEW_MIDONET_URI
[zookeeper]
servers = $ZK_SERVERS
EOL

cat > ~/.midonetrc <<EOL
[cli]
project_id=$PROJECT_ID
password=$PASSWORD
username=$USERNAME
api_url=$NEW_MIDONET_URI
EOL

./migrate.py -c mig.conf migrate < data_prep.json 2> migrate.log

if [ $PR2ER = "TRUE" ]; then
    ./migrate.py -c mig.conf pr2er < data_prep.json 2> pr2er.log
fi

if [ $EXTRAROUTES = "TRUE" ]; then
    ./migrate.py -c mig.conf extraroutes < data_prep.json 2> extraroutes.log
fi

if [ $ANTISPOOF = "TRUE" ]; then
    ./migrate.py -c mig.conf antispoof < data_prep.json 2> antispoof.log
fi

sudo cp /etc/neutron/neutron.conf .
sudo sed -i 's/core_plugin.*/core_plugin = neutron.plugins.midonet.plugin.MidonetPluginV2/g' /etc/neutron/neutron.conf
sudo service neutron-server restart
