---
layout: default
---
# <a name="installation"></a>Installation

Download MatchyPatchy:
<table>
<tr><td>Windows</td><td>LINK</td></tr>
<tr><td>MacOS</td><td>LINK</td></tr>
<tr><td>Ubuntu</td><td>LINK</td></tr>
</table>

Once the installer is downloaded, click ""

Requirements:
For use with Nvida GPU, first install CUDA <a href="">


# <a name="getting-started"></a>Getting Started

Welcome to the MatchyPatchy User Manual! This manual is designed to help you 
get started with MatchyPatchy, a desktop application for aiding in camera 
trap-based re-identification for accurate population assessment. MatchyPatchy
supports both images and video, and the database that is created can be shared 
and exported easily. 

When running MatchyPatchy for the first time, there are a few things to take care of first.


### Project Directory
On first launch, MatchyPatchy will create a folder in the location of the launcher
called "MatchyPatchy-Share" that houses the database, any AI models you download, 
and exported data. 

You can select a different MatchyPatchy-Share folder in Edit > Configuration - Project Directory. 
If you rename the folder, you must update the path in Edit > Configuration - Project Directory.

### Surveys
MatchyPatchy organizes sets of camera trap data by survey. On first launch, MatchyPatchy
will create a Default Survey. To edit the name of this survey, select <b>"Manage Survey"</b>,
select "Default Survey", and press the <b>"Edit"</b> button. 

To add a new survey, press the <b>"+"</b> 
button to add a new survey. A popup will appear. Input the Name of the survey, 
the geographical Region the survey occured in, and the Start and End Year of the 
survey period. You can view surveys by selecting <b>"Manage Surveys"</b>. A popup
with the list of durveys will appear, allowing you to add, edit, and delete surveys.

<!-- Survey Popup -->

### Stations
MatchyPatchy assumes that groups of camera trap images were collected from particular camera
stations. When importing data from a folder of images, such as from a station, you can
select the station name from the folder structure. You can also import multiple stations 
at once, though this requires that the folder hierarchy is consistent across stations, 
i.e. that the station name is at the same "depth" throughout the given directory. 

When importing from a .csv file, make sure there is a column that provides station information. 

<!-- Example folder structure -->

### AI Models
In order to predict potential matches, MatchyPatchy requires MegaDetector and 
a matching algorithm suitable for your species of interest. We also recommend a 
viewpoint detection algorithm to prescreen for impossible matches between different 
sides of the animal. You can download models 
from our server by selecting the File > <b>Download Models</b> option from the menubar.
MatchyPatchy downloads the models into the <i>MatchyPatchy-Share/models</i> directory.

<u>Available models:</u>
<table>
<tr><td>MegaDetector v1000_sorrel</td><td>Standard MegaDetector model</td></tr>
<tr><td>MiewID v3</td><td>Matching algorithm good for big cats, whales, ...</td></tr>
<tr><td>Big Cat Viewpoint</td></tr>
</table>

Once you have added a survey, organized the data by station, and downloaded the 
required models, you are ready to start using MatchyPatchy!

<hr>
# <a name="usage"></a>Using MatchyPatchy

To begin using MatchyPatchy to match individuals, select a survey to add camera 
trap data to, or create a new survey. Then follow the steps in the left column
of the home screen. 

<!-- homepage screenshot -->

## 1. Import Data
MatchyPatchy supports importing raw data from a folder, as well as from a .csv.
The .csv can contain preprocessed information such as bounding boxes, timestamps, etc.

### From a Folder
To import a folder of images, select Step 1. Import from Folder and select the 
desired folder in the browser popup. Then select the level in the folder tree 
that refers to the camera trap Station and then press okay.

MatchyPatchy can import multiple stations at 
once if they are all contained in a single higher-level directory. However, all of the
Station folders must be at the same depth within the directory.  Select the level
that corresponds to Station from the example path and then press OK.

<!--file tree example -->

### From a .CSV
You can import a pre-processed spreadsheet that contains information about the images.
MatchyPatchy can accept the following information as columns:

- filepath (full path required)
- timestamp (required)
- station (required)  
- 

The names in the spreadsheet do not have to be identical to the ones above. 
Once you select a .csv file to import MatchyPatchy will ask you to associate 
columns in the .csv file to the information it can accept. The full filepaths 
to the images that can be accessed from your machine, timestamps, and
station names are required fields. If your .csv does not contain a column that 
conveys the optional information, leave the column selection to "None".

## 2. Process
After importing images by either selecting a folder or .csv file, you must 
then process the data with AI. MatchyPatchy looks for models in the MatchyPatchy-Share/models
folder. You can download models from our server by selecting File > Download Models 
from the menubar.

### Calculate Sequence 
You can optionally check "Calculate Sequence" which will group images together based on 
Station and timestamp.  By default, sequences will have no more than 3 images per 
sequence that occur within 60 seconds. The default images per sequence and sequence
length in seconds can be changed in Edit > Configuration

### Detector Model
If you imported from a folder or if you did *not* import bounding boxes in the .csv file, 
you must first use MegaDetector to automatically extract Regions of Interest (ROIs) 
that closely crop to the animal. 

### Match Embedding
In order to calculate potential matches, each ROI has to processed with an 
embedding extractor such as MiewIDv3. 

### Viewpoint
For some species, we offer a viewpoint model that determines whether the animal
is facing left or right. MatchyPatchy will then only offer potential matches 
with the same viewpoint or if no viewpoint is selected for one of the 
Viewpoint can be manually input or edited in the Media page. 

## 3. Validate
<!-- Media Table Screen -->

Before beginning the matching process, we recommend validating the AI output.
This step will bring you to a table that lists all of the animals identified in
the images or videos, as well as associated metadata. From here you can verify that 
each ROI contains a single animal. You can return to the Home screen or continue
to the Match screen by pressing the corresponding buttons. 

To view the full images, select "Full Images" from the <b>"Show:"</b> dropdown menu.

### Editing the Table
You can edit the table directly by double-clicking a cell and inputing the desired value.
Certain fields are not editable, such as Filepath and Station (marked with * below).
You can edit a row by double-clicking on the row number to the left. This will show
a popup that contains the image and metadata, including editable fields.  

You can edit multiple images at once by checking the boxes under the "Select" column
and pressing <b>"Edit"</b>. To select all images, press "Select All". 

NOTE: To save any changes, press the <b>Save</b> button.  
To undo changes before saving, press the <b>Undo</b> button.

### Filtering the Table
You can filter images by Region, Survey, Station and Viewpoint by selecting them from
the dropdown. You can also filter for unidentified ROIs or favorited media by 
checking the boxes next to those options. To apply selected filters, press <b>Apply 
Filters</b>.


### Table Information

The ROIs contain the following information:

<u>Filepath*</u><br>
The local filepath 

<u>Timestamp*</u><br>

<u>Station*</u><br>

<u>Camera*</u><br>

<u>Sequence ID*</u><br>

<u>External ID*</u><br>
This refers 

<u>Viewpoint</u><br>

<u>Individual</u><br>

<u>Sex</u><br>


<u>Age</u><br>

<u>Reviewed</u><br>
If checked, this ROI was given an ID from the Match screen.

<u>Favorite</u><br>
If checked, this ROI was marked for future lookup and quality control.

<u>Comment</u><br>
This is an editable text field in which you can input any extra information or comments.


The Full Images contain the following information:


## 4. Match
<!-- Match Screen -->
Once you have validated that each ROI contains a single animal and that all station
names and viewpoints are correct, select Step 4. Match from the Home page or from within
the Media page. 

By default, MatchyPatchy calculates the cosine distance between each embedding vector
and presents only potential matches with a distance below than 0.5. You can change 
this threshold using the slider (or input a number directly), as well as calculate
the L2 distance instead. MatchyPatchy will only show potential matches that are of the 
same viewpoint of the animal, and are not from the same sequence or individual already.
Potential match sequences are sorted by distances, with priority given to previously
identified ROIs.  

When you believe the image on the right side is a match for the query image on the left,
select the "Match" button in the center or by pressing "M" on your keyboard. 
If the match image does not have an individual ID, a popup will appear to allow 
you to create a new name. If you can tell the animal's sex and age from the images, 
you can input that information at this time as well.

Move through each potential match by pressing the << and >> buttons on the Match (right) side
or the Left and Right arrow keys on the keyboard. Once you have determined which potential
matches are confirmed for that sequence, you can move to the next sequence.  Move
through sequences by pressing the << and >> buttons on the Query (left) side or 
the Up and Down arrow keys on the keyboard. At any point, you can press "Recalculate 
Matches" to filter out all confirmed matches that have been made so far. 

## 5. Export
You can export the entire database as a .csv by selecting Step 5. Export. See 
<a href="#export">Export and Sharing</a> for more information.


### Sharing a Database
You can move and share the entire MatchyPatchy-Share directory. Be sure to set 
the correct path to the directory by selecting Edit > Configuration - Project Directory.
MatchyPatchy will verify that the 

<hr>
# <a name="quality-control"></a>Quality Control

After you have identified every image, you can verify the labels by selecting 
<b>4. Match</b> from the home screen and then selecting <b>Query by Individual</b>.
This will place every named individual in the query cue and put every example image
for that individual in both the query and match sides. This allows you to compare 
each example of an individual against each other example to confirm that all belong
to that individual. It is recommended that viewpoint is determined for all ROIs 
prior to starting Quality Control. 

<!-- screenshot -->

<hr>
# <a name="troubleshooting"></a>Troubleshooting
### Importing from a Folder


### Database Management

Surveys

Stations

Media

Individuals



<hr>
<h2 class="post-list-heading">Release Notes</h2>
<ul class="post-list"><li><span class="post-meta">Oct 13, 2025</span>
    <h3>
 <a class="post-link" href="/jekyll/update/2025/10/13/welcome-to-jekyll.html">v1.0.0</a>
    </h3></li></ul>
