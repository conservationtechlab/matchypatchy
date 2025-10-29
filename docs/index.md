---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
---
# <a name="installation"></a>Installation

Download Installer:
<table>
<tr><td>Windows</td><td>LINK</td></tr>
<tr><td>MacOS</td><td>LINK</td></tr>
<tr><td>Ubuntu</td><td>LINK</td></tr>
</table>

Once the installer is downloaded, click ""

Requirements:


# <a name="getting-started"></a>Getting Started

Welcome to the MatchyPatchy User Manual! This manual is designed to help you 
get started with MatchyPatchy, a desktop application for aiding in camera 
trap-based re-identification for accurate population assessment. MatchyPatchy
supports both images and video, and the database that is created can be shared 
and exported easily. 

When running MatchyPatchy for the first time, there are a few things to take care of first.

<!-- Survey Popup -->

### Project Directory
On first launch, MatchyPatchy will create a folder called "MatchyPatchy-Share" 
that houses the database, any AI models you download, and exported data. 

You can select a different MatchyPatchy-Share folder in Configuration - Project Directory. 
If you rename the folder, you must update the path in Configuration - Project Directory.

### Surveys
MatchyPatchy organizes sets of camera trap data by survey. To add camera trap
data to MatchyPatchy, you must first create a survey. Press the <b>"+"</b> 
button to add a new survey. A popup will appear. Input the Name of the survey, 
the geographical Region the survey occured in, and the Start and End Year of the 
survey period. You can view surveys by selecting <b>"Manage Surveys"</b>. A popup
with the list of durveys will appear, allowing you to add, edit, and delete surveys.

<!-- Survey Popup -->

### Stations
MatchyPatchy assumes that camera trap images were collected from particular camera
stations. When importing data from a folder, MatchyPatchy will attempt to determine
the station name from the folder structure. This requires that the folder hierarchy
is consistent across stations, i.e. that the station name is at the same "depth"
throughout. When importing from a .csv file, make sure there is a column that provides
station information. 

### AI Models
In order to predict potential matches, MatchyPatchy requires MegaDetector and 
a matching algorithm suitable for your species of interest. We also recommend a 
viewpoint detection algorithm to prescreen for impossible matches between different 
sides of the animal. You can download models 
from our server by selecting the <b>Download Models</b> option on the homescreen.
MatchyPatchy downloads the models into the <i>MatchyPatchy-Share/models</i> directory.


<u>Available models:</u>
<table>
<tr><td>MegaDetector v5a</td><td>Standard MegaDetector model</td></tr>
<tr><td>MegaDetector v5b</td><td>Standard MegaDetector model</td></tr>
<tr><td>MiewID v3</td><td>Matching algorithm good for big cats, whales, ...</td></tr>
<tr><td>Big Cat Viewpoint</td></tr>
</table>

Once you have added a survey, organized the data by station, and downloaded the 
required models, you are ready to start using MatchyPatchy!

# <a name="usage"></a>Using MatchyPatchy

To begin using MatchyPatchy to match individuals, select a survey to add camera 
trap data to, or create a new survey. Then follow the steps in the middle column
of the home screen. 

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
folder. You can download models from our server 

### Calculate Sequence 
You can optionally check "Calculate Sequence" 

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
Before beginning the matching process, we recommend validating the AI output.
This step will bring you to a table that lists all of the animals identified in
the images or videos, as well as associated metadata.

## 4. Match
Once you have validated that each ROI contains a single animal and that all station
names and viewpoints are correct, select Step 4. Match from the Home page or from within
the Media page. 

By default, MatchyPatchy calculates the cosine distance between each embedding vector
and presents only potential matches with a distance below than 0.5. You can change 
this threshold using the slider (or input a number directly), as well as calculate
the L2 distance instead. MatchyPatchy will only show potential matches that are of the 
same viewpoint of the animal, and are not from the same sequence or individual already. 

When you believe the image on the right side is a match for the query image on the left,
select the "Match" button in the center or by pressing "M" on your keyboard. 
If the match image does not have an individual ID, a popup will appear to allow 
you to create a new name. If you can tell the animal's sex and age from the images, 
you can input that information at this time as well.

Move through each potential match by pressing the << and >> buttons or the 
Left and Right arrow keys on the keyboard. Once you have determined which potential
matches are confirmed for 

## 5. Export
You can export the entire database by selecting Step 5. Export. 

# <a name="quality-control"></a>Quality Control

After you have identified every image, you can verify the labels by selecting 
<b>4. Match</b> from the home screen and then selecting <b>Query by Individual</b>.
This will place every named individual in the query cue and put every example image
for that individual in both the query and match sides. This allows you to compare 
each example of an individual against each other example to confirm that all belong
to that individual. 

<!-- screenshot -->

# <a name="export"></a>Export and Sharing

You can export the database as a spreadsheet by navigating to the home screen and 
selecting <b>5. Export</b>. 

### Sharing a Database


# <a name="troubleshooting"></a>Troubleshooting
### Importing from a Folder

<hr>

<h2 class="post-list-heading">Release Notes</h2>
<ul class="post-list"><li><span class="post-meta">Oct 13, 2025</span>
    <h3>
 <a class="post-link" href="/jekyll/update/2025/10/13/welcome-to-jekyll.html">v1.0.0</a>
    </h3></li></ul>
