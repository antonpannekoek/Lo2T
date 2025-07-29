# LOFAR 2.0 triggering software

Example usage:

```
> python -m lo2t.receiver -h
usage: receiver.py [-h] [-c CONFIGFILE] [-v] [-t TEST_MESSAGE]

Receive Kafka GCN messages and process these

options:
  -h, --help            show this help message and exit
  -c, --configfile CONFIGFILE
                        Path to configuration file (default: config.toml)
  -v, --verbose         Verbosity level, repeat to increase verbosity (default: 0)
  -t, --test_message TEST_MESSAGE
                        Test message to process (default: )
> python -m lo2t.receiver -c credentials.toml -v
```

An example configuration file is provided in `kitchensink.toml`. To use Lo2t,
you will need to register at NASA GCN and input your credentials in a copy of
this file.
