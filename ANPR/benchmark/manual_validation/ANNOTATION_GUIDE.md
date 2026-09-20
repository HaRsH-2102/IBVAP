# ANPR Manual Annotation Guide

This guide explains how to use the local annotation tool to generate the ground-truth annotations for the ANPR benchmark validation set.

## 1. How to Start Annotation
Open your terminal and run:
```powershell
cd e:\ANPR
conda activate e:\ANPR\environments\benchmark
python benchmark\manual_validation\annotate.py
```
This will launch an OpenCV window displaying the first image.

## 2. Interface and Navigation
* **`n` or Right Arrow**: Move to the **NEXT** image.
* **`p` or Left Arrow**: Move to the **PREVIOUS** image.
* The current image number and filename (e.g., `Image 17 / 50 : AP27.jpg`) are displayed at the top left of the screen.

## 3. How to Annotate a Plate (Bounding Box & Text)
1. Using your mouse, **click and drag** a rectangle tightly around the license plate.
2. When you release the mouse button, the OpenCV window will pause.
3. Look at your **terminal/command prompt**. It will ask you for:
   * **`Enter ground truth plate text:`** (Type the actual plate text manually, e.g., `MH12AB1234`).
   * **`Enter condition:`** (Type the condition from the list below, or leave empty).
   * **`Enter notes:`** (Optional, type any specific notes or leave empty).
4. Press Enter. The OpenCV window will resume, and the blue bounding box with your text will now be saved and drawn on the image.

## 4. How to Annotate Multiple Plates
If there are multiple vehicles/plates in the same image, simply **drag a new box** around the second plate. The terminal will prompt you again. Both plates will be saved under the same image in the CSV.

## 5. How to Mark Unreadable or No Plates
* If an image contains a plate but it is completely unreadable due to blur/glare, press **`u`**. This will mark the image as `UNREADABLE`.
* If an image contains no vehicle or no license plate at all, press **`m`**. This will mark the image as `NO_PLATE`.

## 6. How to Correct Mistakes
* If you make a mistake on an image, press **`d`**. This will **delete all annotations** for the current image. You can then redraw them.

## 7. How to Save and Resume
* The tool **saves automatically** to `ground_truth.csv` every time you add an annotation, delete an annotation, or quit. 
* To quit safely, press **`q`**. 
* To resume later, just run the script again. Your previous annotations will load automatically and be drawn on the images as you navigate.

## 8. Condition Labels
When prompted for a condition in the terminal, you can type one of the following (case-insensitive):
* `CLEAR` (Perfectly visible)
* `SMALL` (Very small/far away)
* `BLUR` (Motion blur or out of focus)
* `NIGHT` (Low light)
* `GLARE` (Reflections or headlights blocking characters)
* `ANGLE` (Highly skewed perspective)
* `OCCLUSION` (Partially blocked by an object)
* `TWO_LINE` (HSRP two-line square plates)
* `MOTORCYCLE`
* `CAR`
* `TRUCK`
* `BUS`
* `OTHER`
