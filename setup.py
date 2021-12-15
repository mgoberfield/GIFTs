import os
import sys
import setuptools

setuptools.setup()
#
# Find skyfield module location
try:
    #
    # If skyfield was installed before GIFTs
    import skyfield

    bsp_directory = os.path.join(skyfield.__path__[0], 'bsp_files')
    if not os.path.exists(bsp_directory):
        os.mkdir(bsp_directory)
        os.chmod(bsp_directory, 0o777)

except ModuleNotFoundError:
    #
    # Newly installed with GIFTs
    site_package_dir = os.path.join(sys.prefix, 'lib', 'python{}.{}'.format(sys.version_info.major,
                                                                            sys.version_info.minor), 'site-packages')
    egg_ext = '-py{}.{}.egg'.format(sys.version_info.major, sys.version_info.minor)

    for d in os.listdir(site_package_dir):
        if d.startswith('skyfield') and d.endswith(egg_ext):
            os.mkdir(os.path.join(site_package_dir, d, 'skyfield', 'bsp_files'))
            os.chmod(os.path.join(site_package_dir, d, 'skyfield', 'bsp_files'), 0o777)
            break
    else:
        print("Unable to create bsp_files directory for skyfield module. Please create it manually with user & group "
              "write permissions")
