import os
import subprocess

from nmigen.build import *
from nmigen.vendor.lattice_ecp5 import *
from .resources import *

__all__ = ["ULX4MPlatform"]

class ULX4MPlatform(LatticeECP5Platform):
    device      = "LFE5UM-85F"
    package     = "BG381"
    speed       = "8"
    default_clk = "clk25"
#    default_rst = "rst"

    def __init__(self, *, VCCIO1="2V5", VCCIO6="3V3", **kwargs):
        """
        VCCIO1 is connected by default to 2.5 V via R100 (can be set to 3.3 V by disconnecting
        R100 and connecting R105)
        VCCIO6 is connected to 3.3 V by default via R99 (can be switched to 2.5 V with R104,
        see page 51 in the ECP5-5G-EVN datasheet)
        """
        super().__init__(**kwargs)
        assert VCCIO1 in ("3V3", "2V5")
        assert VCCIO6 in ("3V3", "2V5")
        self._VCCIO1 = VCCIO1
        self._VCCIO6 = VCCIO6

    def _vccio_to_iostandard(self, vccio):
        if vccio == "2V5":
            return "LVCMOS25"
        if vccio == "3V3":
            return "LVCMOS33"
        assert False

    def bank1_iostandard(self):
        return self._vccio_to_iostandard(self._VCCIO1)

    def bank6_iostandard(self):
        return self._vccio_to_iostandard(self._VCCIO6)

    resources   = [
        #Resource("rst", 0, PinsN("C3", dir="i"), Attrs(IO_TYPE="LVCMOS33")),
        Resource("clk25", 0, Pins("G2", dir="i"),
                 Clock(25e6), Attrs(IO_TYPE="LVCMOS33")),

        # By default this CLK is not populated, see User Manual Section 4.
        #Resource("extclk", 0, Pins("B11", dir="i"),
                 #Attrs(IO_TYPE="LVCMOS33")),

        *LEDResources(pins="B2 B1 B3 C1",
            attrs=Attrs(IO_TYPE="LVCMOS33", DRIVE="4")),
        *ButtonResources(pins="C3 C2",
            attrs=Attrs(IO_TYPE="LVCMOS33", PULLMODE="DOWN")),

        # FTDI connection.
        #UARTResource(0, uart_rx="N3", uart_tx="N4", role="dce",attrs=Attrs(IO_TYPE="LVCMOS33")),
        #UARTResource(0,rx="N3", tx="N4",attrs=Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP")),

        Resource("uart_tx", 0, Pins("N4", dir="o"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP")),
        Resource("uart_rx", 0, Pins("N3", dir="i"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP")),

        Resource("uart_tx_enable", 0, Pins("T1", dir="o"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP")),

        *SDCardResources(0,
            clk="J1", cmd="J3", dat0="K2", dat1="K1", dat2="H2", dat3="H1",
            attrs=Attrs(IO_TYPE="LVCMOS33", SLEW="FAST")
        ),

        # SPI Flash clock is accessed via USR_MCLK instance.
        Resource("spi_flash", 0,
            Subsignal("cs",   PinsN("R2", dir="o")),
            Subsignal("copi", Pins("W2", dir="o")),
            Subsignal("cipo", Pins("V2", dir="i")),
            Subsignal("hold", PinsN("W1", dir="o")),
            Subsignal("wp",   PinsN("Y2", dir="o")),
            Attrs(PULLMODE="NONE", DRIVE="4", IO_TYPE="LVCMOS33")
        ),
        SDRAMResource(0,
            clk="G19", cke="G20", cs_n="P18", we_n="N20", cas_n="N18", ras_n="M18", dqm="P20 D19",
            ba="L18 M20", a="L19 L20 M19 H17 F20 F18 E19 F19 E20 C20 N19 D20 E18",
            dq="U20 T20 U19 T19 T18 T17 R20 P19 H20 J19 K18 J18 H18 J16 K19 J17",
            attrs=Attrs(PULLMODE="NONE", DRIVE="4", SLEWRATE="FAST", IO_TYPE="LVCMOS33")
        ),

        Resource("serdes", 0,
            #Subsignal("tx", DiffPairs("W4", "W5", dir="o")),
            #Subsignal("rx", DiffPairs("Y5", "Y6", dir="i")),
            Subsignal("tx", DiffPairs("W17", "W18", dir="o")),
            Subsignal("rx", DiffPairs("Y16", "Y17", dir="i")),
        ),
        Resource("serdes", 1,
            Subsignal("tx", DiffPairs("W8", "W9", dir="o")),
            Subsignal("rx", DiffPairs("Y7", "Y8", dir="i")),
        ),
        Resource("serdes", 2,
            Subsignal("tx", DiffPairs("W13", "W14", dir="o")),
            Subsignal("rx", DiffPairs("Y14", "Y15", dir="i")),
        ),
        Resource("serdes", 3,
            #Subsignal("tx", DiffPairs("W17", "W18", dir="o")),
            #Subsignal("rx", DiffPairs("Y16", "Y17", dir="i")),
            Subsignal("tx", DiffPairs("W4", "W5", dir="o")),
            Subsignal("rx", DiffPairs("Y5", "Y6", dir="i")),

        ),

        Resource("serdes_clk", 0, DiffPairs("Y11", "Y12", dir="i")),
        Resource("serdes_clk", 1, DiffPairs("Y19", "W20", dir="i")), # 200 MHz

        # TODO: add other resources
    ]
    connectors = [
        Connector("gpio", 0, {
            "0+": "B11",  "0-":  "C11",
        })
    ]


    @property
    def required_tools(self):
        return super().required_tools + [
            "openFPGALoader"
        ]

    def toolchain_prepare(self, fragment, name, **kwargs):
        overrides = dict(ecppack_opts="--compress")
        overrides.update(kwargs)
        return super().toolchain_prepare(fragment, name, **overrides)

    def toolchain_program(self, products, name):
        tool = os.environ.get("OPENFPGALOADER", "openFPGALoader")
        with products.extract("{}.bit".format(name)) as bitstream_filename:
            subprocess.check_call([tool, "-b", "ulx4m", '-m', bitstream_filename])

if __name__ == "__main__":
    from .test.blinky import *
    ULX4MPlatform().build(Blinky(), do_program=True)
