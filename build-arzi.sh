rm -rf ../ports/rp2/build-RPI_PICO_W
rm firmware.uf2
cd python
mkdir build
cd build
mkdir html
cd html
cp -r ../../../html_raw/general/* .
cp -r ../../../html_raw/arzi/* .
gzip -9 ./*
cd ..  # back to /python/build
python3 -m freezefs -s html frozen_html.py
rm -rf html
cp -r ../CommonDrivers/* .
cp ../Manifest/manifest.py .
# copy individual drivers
cp ../IndividualDrivers/asy_i2c_driver.py .
cp ../IndividualDrivers/asy_spi_driver.py .
cp ../IndividualDrivers/asy_fram_driver.py .
cp ../IndividualDrivers/asy_fram_manager.py .
cp ../IndividualDrivers/neopixel_signal.py .
cp ../IndividualDrivers/asy_scd30_driver.py .
cp -r ../IndividualDrivers/asy_sgp40_driver .
cd ../.. # now inside py-include
mkdir temp
mv ../ports/rp2/modules/_boot.py ./temp
cp ./modules/_boot.py ../ports/rp2/modules/
cp ./modules/sensortask-arzi.py ../ports/rp2/modules/sensortask.py
cd .. # now inside basedir

# Use this for new repos for setting up env initially
# make -C mpy-cross/ -j 16
# make -C ports/rp2 BOARD=RPI_PICO_W clean
# make -C ports/rp2 BOARD=RPI_PICO_W submodules

make -C ports/rp2 BOARD=RPI_PICO_W FROZEN_MANIFEST=/home/nico/rpi_pico/micropython/py-include/python/build/manifest.py -j 16
cd py-include
cp ../ports/rp2/build-RPI_PICO_W/firmware.uf2 .
rm ../ports/rp2/modules/_boot.py
rm ../ports/rp2/modules/sensortask.py
mv ./temp/_boot.py ../ports/rp2/modules/
rm -rf ./temp
cd python
rm -rf ./build
cd ..
