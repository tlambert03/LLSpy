* on spimagine preview, openGL error on some windows 10 computers
* backgrounds on vertical sliders on spimagine viewer are screwed up
* When unexpected errors occur mid-processing, sometimes the "cancel" button does nothing, forcing a restart.
* when loading regDir with cloud.json, it doesnt load images, and if you try to show
  an image with something like ``rd.cs.show_matching`` you get an error ``AttributeError: 'FiducialCloud' object has no attribute 'max'``