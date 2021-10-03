# Digitization

Digitization allows to convert an image of Spinorama meaurements into numeric data that can be used in any available analysis or visualization tools. That source Spinoramas can be found for example at a resource such as [https://speakerdata2034.blogspot.com](https://speakerdata2034.blogspot.com)

When digitizing data it is important to follow the convention for naming the dataset (names of the 5 curves that you will digitize). The easiest way to do it and to also get many other settings already pre-set for you is to start from an existing "[template](template Spinorama.tar)" project.

## Prepare source data

Because WebPlotDigitizer 4.2 does not allow to change the image without resetting the project, we start with a workaround by first modifying the template file to load:

1. Open the "template Spinorama.tar" file with an archive editing program, such as 7-Zip. (you can also use any other .tar Spinorama project file as a template)

2. Get the Spinorama image that you want to digitize and rename it to "image.png" (make sure it is a .png file)

3. Replace the "image.png" file inside the archive with your new image. (drag & drop works great in 7-Zip)  Note, the best source file for digitization is usually the "raw" unedited image file, so try to avoid upscaled images when raw data is available.

## Do the digization

1. Open Your modified template "template Spinorama.tar" file by choosing "Load Project" in WebPlotDigitizer 4.2 or newer. (template must already contain the correct Spinorama that you will digitize)

2. Re-define the axis by:

	- select "XY" under "Axes", then press
	- "Delete" (or "Tweak Calibration if you prefer to make adjustments")
	- "Add Calibration"
	- "2D (X-Y) Plot"
	- "Align Axes"
	- and proceed according to instructions to step 3.

3. See the image for recommended settings. Try to pick robust reference points, for example 20000Hz is often poorly defined, so I usually use 10000Hz mark as a reference.

4. If you deleted old "XY" calibration, you will get "Uncalibrated Dataset" warning. This just means that you need to select your "XY" Axes in the Dataset options.

Calibration Quality check: Place cursor at 1000Hz and 80 dB point and check that the program shows correct value under the zoomed-in cursor view.

Now for each of the 5 Datasets:

5. Re-do the "Mask

	- press "Erase" and "Erase All"
	- draw new mask using "Pen" tool

6. Do the Automatic Extraction point extraction:

	- try pressing "Run" with existing settings for Automatic Extraction. In many cases it will give a good result right away,
	- do tweak the settings and re-run the automatic detection several times to get the best starting point. Adjust "Color", "Distance" and deltaX - deltaY values. also adjusting Mask can improve things.

7. After automatic extraction, use Manual editing to fix problems and add extra points:

	- Remove obviously wrong points.
	- Try to place a point on each peak! (if there is a wavy curve, each local wave extreme should get at least one point). This is especially crucial for On-Axis and Listening Window curves.
	- Try to remove points where data is unreliable (do not digitize data where it is known to be poorly measured)

8. When done, "Save Project" as ".tar" archive where Project name is the name of the Speaker + any important details.

Note, you can always save work-in-progress project and continue working on it later.

When you have your .tar file, it can be imported into for example: https://github.com/pierreaubert/spinorama/
