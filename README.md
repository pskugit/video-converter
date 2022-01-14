# Video Converter
> converts Folder2Video and Video2Folder

This is a small UI program used to convert a video file into a folder containing images of all frames.
Or to convert an image folder into a video file given the set parameters.

## Prerequisites

Written in Python3, the program has a few external libraries.  

```
pip install -r requirement.txt
```

## Usage

### Folder to video

Build a .mp4 file from a folder containing only .jpg or .png images.

![](/images/vm1.JPG?raw=true "Optional Title")

Parameters to be chosen:

- `max length`: the maximal number of distinct images that are loaded from the image folder. If `0`, all image files are used.
- `size`: specified video resolution, eg. `1024x1000`. Larger images will be cropped. If `0x0`, the size of the first image is used. 
- `fps`: frames per second. The number of images shown in one second of video.
- `repeat`: repeats ever image n times. 

Example: if fps=1 and repeat=5, a video is created that shows every image for 5 seconds. Which in that case is more like a slideshow.

### Video to folder

Extract all individual frames of a video file and save them as .png to a folder.

![](/images/vm2.JPG?raw=true "Optional Title")

This mode has no parameters to specify.


## Meta

Philipp Skudlik 

[https://github.com/pskugit](https://github.com/pskugit/)

