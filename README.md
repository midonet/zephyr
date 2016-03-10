Zephyr ~ A Lightweight Neutron Testing System
=============================================


Introduction
------------

Zephyr is a lightweight framework for neutron API and backend testing.
In its basic operation, it will either create a physical topology or connect
to a pre-existing topology (such as one started by devstack, or other tools)
then provide access to the virtual topology API to construct a virtual
topology directly (i.e. using the Neutron API).  Zephyr can then execute any
number of situational tests against the created topologies and report the
results via text printout and/or JUnit XML.

### Design Principles

The design document for Zephyr (up-to-date and public), can be found
[here](https://docs.google.com/a/midokura.com/document/d/1q-VMigoJokCUkrC7eW3RWDmuiXDH-1W_mui8yv7IDvY/edit?usp=sharing).

Please reference that document for charts and design graphics which will
supplement the text in this document.

Zephyr was written with the following design principles in mind:

* Neutron-Based - Limit the Openstack components to the networking API only
to keep the installation complexity to a  minimum and focus the testing on
network functionality.
* Highly Componentized - Each piece should operate at an interface level
so backends and implementations can be swapped out easily.  This especially
is necessary with the physical and virtual layer interactions.
* Vendor Agnostic - Zephyr should run using a pluggable physical layer model
and a pluggable API to the virtual layer.  Any backend vendor should be able
to start and configure their software via Zephyr and write tests.
* Both Customized and Upstream Test Support - Tests written in Zephyr can
be generalized to work across a variety of different vendor plugins as well
as customized, vendor-specific tests which might be useful for a particular
backend implementation.  These customized tests can be maintained by the
networking-* vendors separate from the tests common to all neutron API
plugins.


Zephyr Organization
-------------------

### Components

Zephyr is organized into three main components and two helper components.  The
main components are:

* ptm - Physical Topology Manager - Handles setup, teardown, management,
modification, and analysis of the physical layer.  This is what simulates the
"bare iron" in the test environment.  It is responsible for direct access to and
from the operating system and OS layer applications (i.e. tcpdump, mz, etc.). When
it comes to an already existing physical topology (e.g. through devstack, or with
a multi-node physical environment), this layer is responsible for connecting
to the physical layer and enabling the virtual layer to communicate with the
already-existing physical topology (shell commands, managing ports and networks,
etc.).
* vtm - Virtual Topology Manager - Handles access to the virtual topology
via an API object.  In the default case, this is a Neutron client object,
but specific vendor's API clients can be used.  There are several helper functions
for topology setup and teardown as well as an encapsulation of a simulated VM
(VMs can be simulated through IP net namespaces, docker containers, or even be
actual VMs created through vagrant, kvm, by nova, etc.), which allows for easy
creation, deletion, modification, and access to these nodes.
* tsm - Test System Manager - Handles the test system, including configuration,
startup, runtime, cleanup, recording of tests and their results.

The helper components are:

* common - Common utilities for all components, including representations of
IP addresses, libraries for tcpdump and PCAP-Filter, OS command-line interfaces,
etc.
* cbt - Utilities which are in charge of configuring the system, including
installation and version control of vendor-specific packages.

### Tests

Tests run against a supplied physical topology.  Tests also have some control
over a) which physical topology features it would be compatible with (for
instance, a test which must run VMs on different hypervisors couldn't run on a
topology with only one hypervisor), and b) modifying the existing physical
topology through the ptm.  Tests can also control VMs directly.

Tests are organized into TestCase and TestSuite organizational structures, ala
unittest, nose, etc.  These are used to organize the order in which the tests run,
but do not affect the topology creation or configuration.  Each TestCase has one
or more test functions.  Test suites in Zephyr are logical only, and are used to
encapsulate a single TestCase (with 1 or more test functions). An entire test run,
from start to finish, will run against a single specified physical topology.  To
run against multiple topologies, simply re-run the tsm and specify the new
topology.

### Test and component interactions

Tests use ptm fixtures to affect the physical system before and after tests are
executed.  For example, the NeutronDatabaseFixture will set up the Neutron
database with some default networks and security groups, as well as completely
drop the Neutron database and recreate a fresh one from scratch when tests are
finished.  Needless to say, this behavior is not desired in all cases, so fixtures
can be configured and set up to enable or bypass this functionality.  Furthermore,
this sort of setup should only happen once, so fixtures are put into the ptm to
affect the physical system once, after the ptm is started, and once, after the ptm
is shutdown.

Aside from this, when it comes to any virtual setup, the tests are responsible for
cleaning up and leaving the Neutron database in the same state at which the tests
were started from.  This is to ensure non-interference with future tests.  And as
helper functions for normal virtual topology creation events are not provided in
Zephyr, this task must be left to the test writer.


Running Zephyr
--------------

### Configuration

Configuration of Zephyr is done via JSON files by default (although this is
configurable).

#### ptm Configuration

The ptm is configured via physical topology configuration files (JSON by default).
Each ptm implementation will have its own configuration, as the needs of different
implementations would likely require different configuration data (for example,
an already existing physical topology wouldn't need to have data on what applications
and what other hosts to start, only a set of IPs, net namespaces, container names,
etc. to connect to).

##### Sample ptm Configuration

This [example configuration file](config/physical_topologies/2z-2c.json) is specific
to the `ConfiguredHostPTMImpl` ptm implementation.  Other ptm implementations may
use a different configuration schema.

This configuration creates a root host, two zookeeper hosts, two compute nodes, and a
network controller.  The root host has a Linux bridge created, and each host has
several interfaces defined with IP addresses where applicable, which will be wired
together in the `wired` section.  This section simulates actually plugging in wires
to the interfaces.

The `implementation` section nails down the abstract topology
to the actual Python classes which will be used.  This specifies the host classes
for each host as well as a list of application classes which will run on the host.
Any application-specific parameters are also supplied (like IP address configuration,
ID numbers, etc.).

Finally, the `host_start_order` will dictate the order in which hosts are started
using "tiers" of parallel starts.  Each "tier" is a list of hosts to start in
parallel, and then wait for startup completion before proceeding to the next "tier."
In the example above, the root node will start and finish starting up before the
zookeeper nodes.  The two compute nodes will start in parallel, but both will finish
starting and be ready before the network node is started.

#### Application-specific Config

Applications, backend APIs, and other custom components can all use configuration
files as needed.  The _config_ directory is available for any other configuration
in addition to the ptm config files.

### Starting up the physical topology only

The `ptm-ctl.py` script is responsible for creating and starting the physical
topology.  This, of course, only makes sense if a configured topology is used.  If
a pre-existing topology is in place, this script shouldn't be used.

The command options are:

| Command             | Description                                                            |
| ------------------- | ---------------------------------------------------------------------- |
| --startup           | Start a ConfiguredHostPTMImpl based on the config                      |
| --shutdown          | Shutdown the ConfiguredHostPTMImpl based on the config                 |
| --print             | Print the topology specified in the config (do nothing otherwise)      |
| --features          | Print the topology features supported and set by ConfiguredHostPTMImpl |
| --config-file FILE  | Specify the topology file to use                                       |
| -d                  | Turn on debug mode for logging                                         |
| -h                  | Print out help, including a full list of options                       |



### Running a full test suite

The `tsm-run.py` script is used to launch the tsm and run tests.  This also will
specify the physical topology to use, and will be the main point of entry into
Zephyr for the majority of cases.

| Command               | Description                                                       | Default                                       |
| --------------------- | ------------------------------------------------------------------| --------------------------------------------- |
| -t TESTS              | Specify the tests to run (see below)                              | None                                          |
| -n NAME               | Specify the name of this test run for reporting purposes          | TIMESTAMP                                     |
| -c CLIENT             | Specify the client API to use ('neutron', 'midonet')              | 'neutron'                                     |
| -a AUTH               | Specify authentication scheme to use ('keystone', 'noauth')       | 'noauth'                                      |
| --client-args ARGS    | Specify client params (see below)                                 | None                                          |
| -p CLASS              | Specify the PTMImpl class to use as the ptm implementation        | 'ptm.impl.ConfiguredHostPTMImpl'              |
| -o <topology>         | Specify the topology config file to use                           | 'config/physical_topologies/2z-3c-2edge.json' |
| -d                    | Turn on debug mode for logging                                    | False                                         |
| -l                    | Specify the logging directory                                     | '/tmp/zephyr/logs'                            |
| -r                    | Specify the directory to place any test results (as JUnit XML)    | '/tmp/zephyr/results'                         |
| -h                    | Print out help, including a full list of options                  | N/A                                           |

#### Note on TESTS:

The TESTS parameter to `-t` should be a comma-delimited list with no spaces.  Each test
should either be:

1. A fully qualified name of a Python module (.py/.pyc file - without the extension)
2. A fully qualified name of a Python class and/or function
3. A fully qualified name of a Python package

Using (1) will inspect all classes in the module for functions which start with "test"
and run each in order.

Using (2) will inspect the given class for functions which start with "test", or (if given)
run the specified function.

Using (3) will inspect every Python module file in the package directory and all
subdirectories (recursively on down the tree) and run on each module found (ala option (a))

For example:

+ (1) `-t tests.neutron.reliability.test_basic_ping`
+ (2) `-t tests.neutron.reliability.test_basic_ping.TestBasicPing`
+ (2) `-t tests.neutron.reliability.test_basic_ping.TestBasicPing.test_neutron_api_ping_two_hosts_same_hv`
+ (3) `-t tests.neutron.reliability`
+ (3) `-t tests.neutron`

#### Note on Client ARGS

The ARGS parameter to `--client-args` is used when creating the client in Python.  As
all clients must have an __init__ constructor with parameters, the arguments to this
constructor can be specified here.  A couple are set with other arguments (for example
`-a AUTH` sets the `auth_strategy` parameter to Neutron Client along with `auth_url`,
`username`, `password`, and `tenant_name` from `OS_` env vars if "keystone" is used)),
but most can be specified and/or overridden here.

This list should be in the form of param=value,param=value,... with commas separating the
param/value pairs, and no spaces.  If a space is necessary for a parameter, try enclosing
the entire ARGS parameter in quotes.


Writing Tests for Zephyr
------------------------

(In progress)


Improving Zephyr
----------------

(In progress)

References
----------

* Zephyr Design Doc - https://docs.google.com/a/midokura.com/document/d/1q-VMigoJokCUkrC7eW3RWDmuiXDH-1W_mui8yv7IDvY/edit?usp=sharing
