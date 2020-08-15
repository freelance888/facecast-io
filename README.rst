***********
Facecast IO
***********

Unofficial API client to https://facecast.io service
####################################################

Installation
************

:pip: pip install facecast-io
:poetry: poetry add facecast-io

Usage as a library
******************

::

    api = FacecastAPI(os.environ["FACECAST_USERNAME"], os.environ["FACECAST_PASSWORD"])
    # display available devices
    print(api.devices)

    # get device by name
    d = api.devices['Dev name']

    # delete specific device and all devices
    api.devices.delete_device('Dev name')
    api.devices.delete_all()

    # create device
    api.devices.create_device('Dev name')

    # display device server url and key
    print(d.input_params)

    # display outputs of device
    print(d.outputs)

    # create new output
    d.create_output("Youtube", 'rtmp://a.youtube.com', 'youtube-key')

    # start/stop output
    d.start_outputs()
    d.stop_outputs()

    # delete all outputs
    d.delete_outputs()


Usage in command line mode
**************************
First of all you need to login into your Facecast.io account:
::

    $ python -m facecast_io login

Now you're able to work with your devices. Some of useful commands.

Check all existing devices:
::

    $ python -m facecast_io devices list

Create new device
::

    $ python -m facecast_io devices create somename

Show info about specific device
::

    $ python -m facecast_io device someone

Show stream params for device
::

    $ python -m facecast_io device someone --input

Start and stop outputs for device
::

    $ python -m facecast_io device someone --start
    $ python -m facecast_io device someone --stop

Provision data from API into Facecast. If we have pipeline that send following structure:
::

    [
      {
        "channel_name": "YT ALLATRA TV Italia",
        "server_url": "url",
        "stream_key": "key",
      },
    ]

Call command would be next:
::

    $ http GET 'https://streams.com/some' | jq .devname | python -m facecast_io devices provision devname
