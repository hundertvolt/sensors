rm -rf ../ports/rp2/build-RPI_PICO_W
rm firmware.uf2
cd python
mkdir build
cd build
mkdir html
cd html
cp -r ../../../html_raw/general/* .
cp -r ../../../html_raw/dev/* .
gzip -9 ./*
cd ..  # back to /python/build
python3 -m freezefs -s html frozen_html.py
rm -rf html
cp -r ../CommonDrivers/* .
cp ../Manifest/manifest.py .
# copy individual drivers
cp ../IndividualDrivers/asy_i2c_driver.py .
cp ../IndividualDrivers/asy_spi_driver.py .
cp ../IndividualDrivers/asy_uart.py .
cp ../IndividualDrivers/asy_uart_comm.py .
cp ../IndividualDrivers/asy_fram_driver.py .
cp ../IndividualDrivers/asy_fram_manager.py .
cp ../IndividualDrivers/neopixel_signal.py .
cp ../IndividualDrivers/asy_scd30_driver.py .
cp ../IndividualDrivers/asy_shtc3_driver.py .
cp ../IndividualDrivers/asy_mprls_driver.py .
cp ../IndividualDrivers/asy_isl29125_driver.py .
cp -r ../IndividualDrivers/asy_sgp40_driver .
cd ../.. # now inside py-include
cd .. # now inside basedir

# Use this for new repos for setting up env initially
# make -C mpy-cross/ -j 16
# make -C ports/rp2 BOARD=RPI_PICO_W clean
# make -C ports/rp2 BOARD=RPI_PICO_W submodules

make -C ports/rp2 BOARD=RPI_PICO_W FROZEN_MANIFEST=/home/nico/rpi_pico/micropython/py-include/python/build/manifest.py -j 16
cd py-include
cp ../ports/rp2/build-RPI_PICO_W/firmware.uf2 .
cd python
rm -rf ./build
cd ..
