# USI Resolver and Displayer for Metabolomics

This tool is meant to be able to show summarize USI's from various sources. It will achieve the following goals


1. Enable creation of embeddable images in publications that will link out to viewable/interactable spectrum plots
2. 3rd party embedding for visualization of spectra that exist in reposities (e.g. MassIVE, PRIDE, PeptideAtlas)
3. 3rd party embedding of qrcode

Supported USI Types

1. GNPS Molecular Networking Clustered Spectra
2. GNPS Spectral Libraries
3. ProteoXchange Repository Data

## Example USI URLs

### MS2LDA

[mzspec:MS2LDATASK-38:blah:document:43062](http://localhost:5000/spectrum/?usi=mzspec:MS2LDATASK-38:blah:document:43062)

### GNPS Molecular Networking Spectra

[mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943](http://localhost:5000/spectrum/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943)

### GNPS Library Spectra

[mzspec:GNPSLIBRARY:CCMSLIB00005436077](http://localhost:5000/spectrum/?usi=mzspec:GNPSLIBRARY:CCMSLIB00005436077)

### ProteoXchange Repository Data

[mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](http://localhost:5000/spectrum/?usi=mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)


## Deprecated Material

Test URLs for GNPS plotting:

task c95481f0c53d42e78a61bf899e9f9adb
file spectra/specs_ms.mgf
scan 1943

#Spectrum in Molecular Networking
http://localhost:5000/spectrum/?task=c95481f0c53d42e78a61bf899e9f9adb&file=spectra/specs_ms.mgf&scan=1943

#QRCode
http://localhost:5000/qrcode?task=c95481f0c53d42e78a61bf899e9f9adb&file=spectra/specs_ms.mgf&scan=1943

# Example for ms2lda
http://localhost:5000/spectrum/?usi=mzdata:MS2LDATASK-38:blah:document:43062
Note the 38 is the experiment id, 43062 is the document id. blah can be anything!

#Test for GNPS Library Spectrum

