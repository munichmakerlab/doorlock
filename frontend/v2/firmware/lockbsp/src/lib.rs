#![no_std]

pub use rp2040_hal as hal;

extern crate cortex_m_rt;
pub use hal::entry;

#[link_section = ".boot2"]
#[no_mangle]
#[used]
pub static BOOT2_FIRMWARE: [u8; 256] = rp2040_boot2::BOOT_LOADER_W25Q080;

pub use hal::pac;

hal::bsp_pins!(
    Gpio0 { name: rc522_miso },
    Gpio1 { name: rc522_ncs },
    Gpio2 { name: rc522_sck },
    Gpio3 { name: rc522_mosi },
    Gpio4 { name: rc522_nrst },

    Gpio5 { name: buzzer },

    Gpio6 { name: lcd_sda },
    Gpio7 { name: lcd_scl },

    Gpio8 { name: rs485_tx },
    Gpio9 { name: rs485_rx },

    Gpio10 { name: kp_col1 },
    Gpio11 { name: kp_col2 },
    Gpio12 { name: kp_row1 },
    Gpio13 { name: kp_row2 },
    Gpio14 { name: kp_row3 },
    Gpio15 { name: kp_row4 },
    Gpio16 { name: kp_row5 },
    Gpio17 { name: kp_row6 },
    Gpio18 { name: kp_row7 },
    Gpio19 { name: kp_row8 },

    Gpio20 { name: gpio20 },
    Gpio21 { name: gpio21 },
    Gpio22 { name: gpio22 },

    Gpio24 { name: oled_nrst },
    Gpio25 { name: oled_ncs },
    Gpio26 { name: oled_sck },
    Gpio27 { name: oled_mosi },
    Gpio28 { name: oled_dc },
    Gpio29 { name: dbg },
);

pub const XOSC_CRYSTAL_FREQ: u32 = 12_000_000;
