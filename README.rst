
*Object oriented python processing of Lattice Light Sheet Data*

Usage
-----

.. code:: python

    import time

    from clijockey.traits import TraitTable, CUnicode, CUnicodeRegex
    from clijockey.traits import CMacAddressCisco, CIPv4AddressStr
    from clijockey.util import RotatingTOMLLog
    from clijockey.util import Account
    from clijockey.lib import CLIMachine

    # TextFSM template...
    TEMPLATE = """Value INTF (\S+)\nValue IPADDR (\S+)\nValue STATUS (up|down|administratively down)\nValue PROTO (up|down)\n\nStart\n  ^${INTF}\s+${IPADDR}\s+\w+\s+\w+\s+${STATUS}\s+${PROTO} -> Record"""

    # Interfaces() is used to map TextFSM template values to the TOML Log
    class Interfaces(TraitTable):
        intf = CUnicode()  # See the traitlets documentation for CUnicode usage
        addr = CUnicode()
        status = CUnicode()
        # Usage of CUnicodeRegex illustrated below... it errors if no match
        proto = CUnicodeRegex(r'down|up')
        _map = ('intf', 'addr', 'status', 'proto') # TextFSM field order

    # Create a log named rviews_intfs, which automatically rotates at midnight
    #     category must be unique per logging file
    log = RotatingTOMLLog('rviews_intfs', category='route-views')

    ## Define a tuple of username and password pairs here...
    ##    The first is an expected failure to illustrate how it works
    accts = (Account('itsa-mistake', ''), Account('rviews', 'secret2'),)

    ## You can optionally disable auto-enable mode if you like...
    conn = CLIMachine('route-views.routeviews.org', accts,
        auto_priv_mode=False, log_screen=True, debug=False, command_timeout=5)

    conn.execute('term len 0', wait=0.5)    # Wait 0.5 seconds after the cmd
    conn.execute('show version', regex='test>') # regex is another prompt string

    conn.execute('show users', timeout=60)  # 'show users' outputs slowly...
    ## Get the result of the 'show users' command...
    user_output = conn.response

    ## Automatically parse with TextFSM and log to a TOML log
    for ii in range(0, 5):
        intf_list = conn.execute('show ip int brief', template=TEMPLATE)
        for vals in intf_list:
            ## NOTE: info must be a dictionary to be parsed by .write_table_list()
            info = dict(Interfaces(vals))  # <---- This is the info table
            ## Write a timestamped list of tables named 'rview_intf' to the log
            log.write_table_list(table='rview_intf', info=info, timestamp=True)
        time.sleep(1)

    conn.logout()


Installation
------------

Install with pip (-U to auto-upgrade to the latest version) ::

    pip install -U clijockey

Why
---

*Short answer*:

Because libraries like this should "just work" regardless of what you're screen scraping.

*Longer answer*:

I have been writing network screen scraping scripts for fun and profit over the
last two decades; in the process, I have accumulated some opinions about how
things should be done.

As of this writing, there are several similar Python command / response
libraries... some even have a battery of vendor-specific plugins.  The obvious
question is why I think another library is required.  Am I merely guilty of the
`not invented here`_ syndrome?

I hope not.

1.  The popular Python libraries with vendor-specific CLI drivers are
pointlessly finicky and sometimes don't even work for all permutations from
that vendor.  All credit to the tireless souls who write and maintain them, but
I'm tired of hacking around quirks in libraries; I just want to get things done.

2.  Many of the existing libraries drive SSH sessions slowly because they use
paramiko_ (pure-python SSH)

3.  Unit tests should stand alone without needing a real network to test them
on.  This isn't easy when it comes to testing screen scraping, but
`Samuel Abel's`_ `exscript tests`_ are a good example of one way you can do
this well.  I leveraged his ideas in clijockey_

Goals
-----

1.  Maximum flexiblity from a single CLI driver... no vendor-specific plugins.
2.  Get the most common authentication prompt sequences right
3.  Try a list of credentials until one works.
4.  Don't assume the credentials *always* grant enable privs mode
5.  Speed
6.  Optional parsing with TextFSM_ (gtextfsm_ to be exact)
7.  Verbose error messages and debugs.
8.  Support both telnet and ssh
9.  Per-session TOML_ logging (partially implemented)
10. Python3 support (not implemented yet)

Restrictions
------------

clijockey_ only supports `\*nix`_ (OpenSSH_ is required); no Windows support.

Right now, I recommend Python_ 2.x; Python3 support is forthcoming, but a lower
priority

Thanks
------

I am extremely grateful to my employer (`Samsung Data Services`_) for allowing
me to develop parts of this at work.


.. _pexpect: http://https://pexpect.readthedocs.io/en/stable/

.. _`not invented here`: http://dilbert.com/strip/2014-08-12

.. _`Samuel Abel's`: https://github.com/knipknap

.. _`exscript tests`: https://github.com/knipknap/exscript/tree/master/tests

.. _`clijockey`: https://github.com/mpenning/clijockey/

.. _Python: https://python.org/

.. _paramiko: http://www.paramiko.org/

.. _TextFSM: https://github.com/google/textfsm

.. _gtextfsm: https://pypi.python.org/pypi/gtextfsm

.. _OpenSSH: https://www.openssh.com/

.. _`\*nix`: https://en.wikipedia.org/wiki/Unix-like

.. _TOML: https://github.com/toml-lang/toml

.. _`Samsung Data Services`: http://www.samsungsds.com/us/en/index.html