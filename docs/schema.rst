==================  ======================  =================================================================
Key                 Default      		 	Description
==================  ======================  =================================================================
correctFlash        False         			do Flash residual correction
moveCorrected       True	      			move processed corrected files to original LLSdir
flashCorrectTarget  cpu	     				{"cpu", "cuda", "parallel"} for FlashCor
medianFilter        False	     			do Keller median filter
keepCorrected       False	     			save corrected images after processing
trimZ               (0, 0)        			num Z pix to trim off raw data before processing
trimY               (0, 0)        			num Y pix to trim off raw data before processing
trimX               (0, 0)        			num X pix to trim off raw data before processing
nIters              10	        			deconvolution iters
nApodize            15	        			num pixels to soften edge with for decon
nZblend             0	         			num top/bot Z sections to blend to reduce axial ringing
bRotate             False	     			do Rotation to coverslip coordinates
rotate              None	      			angle to use for rotation
saveDeskewedRaw     False	     			whether to save raw deskewed
saveDecon           True	      			whether to save decon stacks
MIP                 (0, 0, 1)    			whether to save XYZ decon MIPs
rMIP                (0, 0, 0)   			whether to save XYZ raw MIPs
mergeMIPs           True	      			do MIP merge into single file (decon)
mergeMIPsraw        True	      			do MIP merge into single file (deskewed)
uint16              True	      			save decon as unsigned int16
uint16raw           True	      			save deskewed raw as unsigned int16
bleachCorrection    False	     			do photobleach correction
doReg               False	     			do channel registration
regRefWave          488	       				reference wavelength when registering
regMode             2step	   				transformation mode when registering
regCalibPath         None	      			directory with registration calibration data
mincount            10	        			minimum number of beads expected in regCal data
reprocess           False	     			reprocess already-done data when processing
tRange              None	      			time range to process (None means all)
cRange              None	      			channel range to process (None means all)
otfDir              None	      			directory to look in for PSFs/OTFs
camparamsPath       None	      			file path to camera Parameters .tif
verbose             0	         			verbosity level when processing {0,1,2}
cropMode            none	    			{manual, auto, none} - auto-cropping based on image content
autoCropSigma       2	         			gaussian blur sigma when autocropping
width               0	         			final width when not autocropping (0 = full)
shift               0	         			crop shift when not autocropping
cropPad             50	        			additional pixels to keep when autocropping
background          -1	        			background to subtract. -1 = autodetect
compressRaw         False	     			do compression of raw data after processing
compressionType     lbzip2	  				compression binary {lbzip2, bzip2, pbzip2, pigz, gzip}
writeLog            True	      			write settings to processinglog.txt
==================  ======================  =================================================================
