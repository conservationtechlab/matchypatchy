# matchypatchy
GUI tool for human validation of AI-powered animal re-identification

TODOS 
 - update match prioritization - id'd and number of matches 
 - add undo for match
 - manage individuals popup
 - filter reviewed/named images
 - keep track of thumbnails for media_table
 - auto compare single individual for QC
 - open image in default image viewer


BIG TODOS
 - make media_table editable, add undo
 - add keypress functionality to compare screen
 - create single image view and popup
 - utilize capture/sequence for viewpoint
 - adjust query to incorporate viewpoint
 - sort compare view by individual instead of sequence


Long Term
 - handle videos
 - in the rare instance that an image has two individuals, build infrastructure to duplicate media entry
   and separate sequence ids, etc
 - adjust station schema to align with camtrapdp deployments schema, CB schema
 - Create function to verify another database
 - cosine distance for knn?