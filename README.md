# Nezu Photo Viewer

A small Windows build tool that creates a NumWorks photo-viewer app from a folder of images. The app is named Gallery on the calculator. Made with ChatGPT Codex.

## Features

- Browse photos with the calculator's left and right arrow keys.
- Supports PNG, JPG/JPEG, WEBP, and BMP.
- Sorts filenames naturally (photo1 comes before photo2).
- Resizes each photo to fit the 320 × 240 display without stretching or cropping. Images are centered on a white background.
- Uses assets/icon.png as the app icon.
- Includes a hidden easter egg.

## Build an app

1. Install Python 3 on Windows if it is not already installed.
2. Double-click build.bat.
3. On the first run, the builder installs Pillow and Node.js and downloads the ARM compiler (about 300 MB). This setup is only needed once.
4. Choose the folder containing your images.
5. Find the generated app at generated/Gallery.nwa.
6. Install the .nwa through [NumWorks Apps](https://my.numworks.com/apps) with your calculator connected.

Subsequent builds are performed locally and can run without an internet connection. The generated folder contains intermediate build files as well as the .nwa app.

## App behavior

- Opens in a 3-column by 3-row photo grid (up to 9 thumbnails per page), with each image fitted to a 4:3 frame and slim gaps between photos.
- Use the arrow keys to navigate; the bottom bar shows the controls.
- Press OK to open the selected photo full-screen.
- Press EXE or Back to return to the grid.
- Right arrow: next photo.
- Left arrow: previous photo.
- Navigation wraps around at the beginning and end of the list.
- Do not turn off the calculator when the gallery is open, this will create a graphic glitch on the screen (Besides that it will not do anything just go back to the Numworks menu.)

Each image is stored as a 320 × 240 RGB565 photo plus a 96 × 72 4:3 grid thumbnail. The pixel data takes about 157 KB per image before any further packaging.

## Tools

The builder checks its local `tools` and `generated` folders and reuses installed dependencies on later builds. Keep the same extracted builder folder when updating it so those dependencies remain available. On a fresh setup, it downloads or installs:

- [Pillow](https://pypi.org/project/Pillow/)
- [Node.js](https://nodejs.org/)
- [nwlink](https://www.npmjs.com/package/nwlink), the NumWorks EADK tool
- [xPack Arm GNU Toolchain](https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack)
