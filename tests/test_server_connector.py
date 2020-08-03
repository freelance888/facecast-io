from time import sleep


def test_create_delete_device(server_connector, device_name):
    assert server_connector.create_device(device_name)
    sleep(5)
    devices = [d for d in server_connector.get_devices() if d.name == device_name]

    assert len(devices) == 1
    device = devices[0]
    assert server_connector.delete_device(device.rtmp_id)
    sleep(5)

    devices = [d for d in server_connector.get_devices() if d.name == device_name]
    assert len(devices) == 0


def test_create_delete_output(server_connector, rtmp_id):
    result = server_connector.create_output(
        rtmp_id, "rtmp://some.com", "sharedkey", "TEST OUTPUT"
    )
    assert result.ok
    assert len(result.outputs) == 1
    output = result.outputs[0]
    server_connector.delete_output(rtmp_id, output.id)
    outputs = server_connector.get_outputs(rtmp_id)
    assert len(outputs) == 0


def test_server_connector(server_connector, rtmp_id):
    device = server_connector.get_device(rtmp_id)
    status = server_connector.get_status(rtmp_id)
    output = server_connector.get_outputs(rtmp_id)
