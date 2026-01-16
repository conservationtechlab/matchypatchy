# MatchyPatchy
<br/>

MatchyPatchy is an open-source GUI tool for human validation of AI-powered animal re-identification.\
It was developed by the San Diego Zoo Wildlife Alliance Conservation Technology Lab.\
Author: Kyra Swanson, (c) 2025
<br/>

---
## Installation

Matchypatchy is a stand-alone executable built in Python. Download it [here](). \
[Github Repository](https://github.com/conservationtechlab/matchypatchy)
<br/>

---
## Getting Started
<br/>

### Download Models
In order to calculate potential matches, MatchyPatchy requires an animal object detector such as [MegaDetector]()
and an embedding extractor such as [MiewID]().  Both models and more can be obtained from the SDZWA server by selecting 
'Download Models' and checking the box associated with which models you want to download.
<br/>

### Select Survey
In order to add media to the database, you must first specify a Survey using 
the dropdown of available surveys. To add a new survey, 

1. Select 'Manage Surveys'
2. Select 'New' 
3. Enter Survey Name
4. Enter Survey Region
5. (Optional) Enter Survey Start Year
6. (Optional) Enter Survey End Year
7. Select 'Ok'
<br/>

### 1. Import Images
Images can be imported via spreadsheet or by manually selecting a directory of images.

**From CSV**
1. Select '1. Import from CSV'
2. Open .csv file
3. Select column headers that correspond to image Filepath, Timestamp, Survey, and Station
4. Optionally select column headers that correspond to image Region, Sequence ID, External ID,
    Viewpoint, Species, Individual ID, and Comment
5. Select 'Ok'
<br/>

**From Folder**
1. Select '1. Import from Folder'
2. Open directory containing image files. Can be a whole Survey containg multiple Stations or single Station.
3. Select the directory level that corresponds to Station name if available
4. Select 'Ok'
<br/>

### 2. Process Images
Run images through a sequence of AI models to obtain predicted matches.\
Note: Models must be accessible in MatchyPatchy's "Models" folder - see Configuration for more.

1. Select '2. Process'
2. (Optional) Check Calculate Sequence (improves performance for videos and images captured in quick succession)
3. **Select Detector Model** - recommended MegaDetector v5a
4. (Optional) Select Species Classifier Model
5. **Select Re-Indentification Model** - required to obtain predicted matches, recommended MiewIDv3
6. (Optional) Select Viewpoint Model (improves performance by estimating animal viewpoint and limiting search space)
<br/>

### 3. Validate 
After processing, this pageview allows you to review the imported media for errors, make changes, delete images, etc.
It can be accessed at any time after image import. 
<br/>

Double-clicking on a cell will allow you to edit it.\
Double-clicking on a single row will pull up a screen to edit multiple fields for an image.\
Selecting one or more row (either by clicking on the row number or checking the select box) will enable the ability
to mass edit particular fields, duplicate entries, or delete entries.
<br/>

The **"Show"** Option allows you view the full images or detected ROIS.\
The **"Save"** Option saves all edits to the database.\
The **"Undo"** Option undoes the last edit made.
<br/>

**Filters** \
Images can be filtered by Region, Survey, Station, Species, and Individual.\
You can also choose to show only "Unidentified" ROIs.\
You can also display all images marked as "Favorite"
<br/>

### 4. Match
After processing, potential matches can be validated at this pageview.
The left side contains a **Query** image and the right side contains potential **Matches**.
If "Calculate Sequence" was selected during the processing stage, the entire **Sequence** will be viewable on the Query side.
The pageview will display the images and associated metadata. 
<br/>

_View Options_\
Adjustments can be made to the **Maximum Number of Matches** shown for each image (within a sequence) and to the maximum distance
threshold between the two images to qualify as a match. The **Cosine** or **L2** distance of the Match from the Query is displayed above the 
match image. Select which distance metric to use in the dropdown. You must select **"Recalculate Matches"** if changes are made to either option
in order to display those changes.\
After matches are validated, you can **"Query by Individual"** to do quality control and ensure all images associated with
an individual are indeed valid.\
Images can be **Filtered** by Region, Survey, or Station to narrow the available matches shown.\
If **"Viewpoint"** was calculated at the processing step, you can filter both the **Query** and the **Match** images by Viewpoint.\
The **"View Data"** Button at the bottom brings you to the Media Validation pageview. 
<br/>

_Image Options_\
You can adjust the **Brightness, Contrast** and **Sharpness** of each image, as well as **Zoom** using the mouse scroll wheel.\
The **"Reset"** button returns the image to its original form.\
The **"Edit Image"** option allows you to make changes to the metadata.\
The **"Open Image"** option opens the image in your default image viewer.\
The **"♥"** option marks the image with the "Favorite" tag.
<br/>

To confirm a match between the Query and the Match image, select the **"Match" button** in the middle, or press the 'M' or 'Space Key'.
Pressing Match again will undo the match, asking you to confirm first.\
You can navigate between Query Sequences and Matches by using the **"<<"** and **">>"** buttons, or by using the arrow keys.\
You can also toggle the **Viewpoint** by pressing 'V'.
<br/>

### 5. Export
The database can be exported as a .csv file. Simply select '5. Export' and specify the file name and location. 
<br/>

---
## Database Management
<br/>

### Definitions
* Survey - An ecological study employing camera traps to investigate wildlife of a particular area.
* Region - A geographical region that may host one or more camera trap surveys.
* Station - Reference to a physical location containing one or camera traps.
* Species - The taxonomic and common names refering to a class of animal.
* Media - Image (and soon video) files obtained from camera traps.
* ROI - Regions of Interest within media files that contain animals. 
* Individual - A particular, singular example of a given species, can be named/ID'd.
* Sequence ID - A unique number associated with a set of sequential images or frames in a video.
* External ID - A unique number used to reference MatchyPatchy output with other datamanagement tools.
* Viewpoint - The side of the body of the animl facing the camera, eg "Left", "Right", "Top"
* Comment - Notes or concerns about a particular media file
* Favorite - A tag marking an image as noteworthy.
<br/>

### Manage Tables
**Survey, Station,** and **Species** tables can be managed independently. 
<br/>

### CSV Import
<br/>


---
## Configuration
<br/>

### Available Models
Models currently available and compatible with MatchyPatchy:\
_Detector Models_:
- MegaDetector v5a
- MegaDetector v5b

_Re-ID Models_: 
- MiewID v3
- MiewID v2

_Viewpoint Models_:
- SDZWA Viewpoint
<br/>

### Link to New Database
Database files can be shared across multiple users of MatchyPatchy. To link to a new .db file, 
<br/>

### Clear Data 
