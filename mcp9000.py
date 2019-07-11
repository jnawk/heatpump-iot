"""
Module for reading the temperature from the MCP9000 Thermocouple
"""
import smbus

class MCP9000(object): # pylint: disable=too-few-public-methods
    """Class for reading the temperature from the MCP9000 Thermocouple"""

    def __init__(self, bus, address):
        self.address = address
        self.bus = smbus.SMBus(bus)

        self.bus.write_byte_data(self.address, 0x05, 0x07)
        self.bus.write_byte_data(self.address, 0x06, 0x7c)

    @property
    def temperature(self):
        """Current temperature"""
        self.bus.write_byte(self.address, 0x00)
        try:
            data = self.bus.read_i2c_block_data(self.address, 0x00, 2)
            return data[0] * 16 + data[1] / 16.0
        except IOError:
            return None
