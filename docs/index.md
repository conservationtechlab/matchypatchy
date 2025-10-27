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

### Surveys
MatchyPatchy organizes sets of camera trap data by survey. To add camera trap
data to MatchyPatchy, you must first create a survey. Press the <b>"+"</b> 
button to add a new survey. A popup will appear. Input the Name of the survey, 
the geographical Region the survey occured in, and the Start and End Year of the 
survey period. You can view surveys by selecting <b>"Manage Surveys"</b>. A popup
with the list of durveys will appear, allowing you to add, edit, and delete surveys.

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


### From a .CSV

## 2. Process
This step will run selected AI algorithms on the data. 

## 3. Validate
Before beginning the matching process, we recommend validating the AI output.
This step will bring you to a table that lists all of the animals identified in
the images or videos, as well as associated metadata.

## 4. Match

## 5. Export


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
