***********
Facecast IO
***********

Unofficial API client to https://facecast.io service
####################################################

Installation
************

:pip: pip install facecast-io
:poetry: poetry add facecast-io

Usage
*****

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



