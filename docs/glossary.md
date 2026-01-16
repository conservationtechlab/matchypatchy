---
layout: glossary
---

# Bounding Box <a name="bounding-box"></a>
The coordinates of a rectangle that define an ROI within an image.
The coordinates are relative to the size of the image (between 0 and 1) 
and are given as:
bbox_x - the x coordinate of the top-left corner of the rectangle
bbox_y - the y coordinate of the top-left corner of the rectangle
bbox_w - the width of the box as a proportion of the whole image
bbox_h - the height of the box as a proportion of the whole image

# Camera <a name="camera"></a>
A physical camera trap device deployed at a Station.

# Capture <a name="capture"></a>


# Detector <a name="detector"></a>
A machine-learning model that is capable of detecting the animals in raw camera trap images (e.g. MegaDetector).

# Distance Metric <a name="distance-metric"></a>
A method for quantifying the dissimilarity of two vectors.

## Cosine Distance 
The cosine of the angle between the vectors, or the dot product of the vectors divided by the product of their lengths.

## L2 Distance
Also known as the Euclidean distance, the straight-line distance between two vectors in n-dimensional space.

## Distance Threshold <a name="distance-threshold"></a>
The upper-bound of the chosen distance metric that will include an image in the match stack
as a potential match when its distance to the query image is below the threshold.

# Embedding <a name="embedding"></a>
The output of the re-identification model that describes the image as a single vector. 

# Individual <a name="individual"></a>
A single, distinct, self-contained living entity. An individual can be given a name,
and has attributes sex and age at a given point in time.  

# Model <a name="model"></a>
In machine learning, a complex algorithm that transforms data of one kind (e.g. a .png image)
into another kind (e.g. a 2,180-point vector) after learning patterns of associations through 
many examples.

# Region <a name="region"></a>
A geographical region that may host one or more Surveys (e.g. "Northest Peru").

# ROI <a name="roi"></a>
A "Region of Interest" within an image that is defined by a bounding box and typically contains
an animal and minimal background.

# Sequence <a name="sequence"></a>
A set of images taken in quick succession at a specific location.
A sequence can also refer to the frames of a video.

# Station <a name="station"></a>
A specific location within the geological bounds of a Survey that contains one or more camera traps.

# Survey <a name="survey"></a>
A camera trap study in a particular geographical Region over a specific period of time
that encompasses a set of cameras at specific Station locations. 

# Viewpoint <a name="viewpoint"></a>
The visible side of the animal's body in an image as seen from the camera. 










