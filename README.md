# USI Resolver and Displayer for Metabolomics

This tool is meant to be able to show summarize USI's from various sources. It will achieve the following goals


1. Enable creation of embeddable images in publications that will link out to viewable/interactable spectrum plots
2. 3rd party embedding for visualization of spectra that exist in reposities (e.g. MassIVE, PRIDE, PeptideAtlas)
3. 3rd party embedding of qrcode

Supported USI Types

1. GNPS Molecular Networking Clustered Spectra
1. GNPS Spectral Libraries
1. ProteoXchange Repository Data
1. MS2LDA Reference Motifs
1. Metabolights Dataset Spectra
1. Metabolomics Workbench Dataset Spectra

![](https://github.com/mwang87/MetabolomicsSpectrumResolver/workflows/unittest/badge.svg)
![](https://github.com/mwang87/MetabolomicsSpectrumResolver/workflows/production-integration/badge.svg)


## Example USI URLs

### MS2LDA

[mzspec:MS2LDATASK-38:document:43062](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MS2LDATASK-38:document:43062)

### MOTIFDB

[mzspec:MOTIFDB:motif:171163](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MOTIFDB:motif:171163)

### GNPS Molecular Networking Spectra

[mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943)

### GNPS Library Spectra

[mzspec:GNPSLIBRARY:CCMSLIB00005436077](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:GNPSLIBRARY:CCMSLIB00005436077)

### Massbank Library Spectra

[mzdata:MASSBANK:BSU00002](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzdata:MASSBANK:BSU00002)

### ProteoXchange Repository Data

[mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)

### MassIVE/GNPS Repository Data

[mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)
[mzdata:MSV000078556:m0__RA10_01_2335:scan:604](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzdata:MSV000078556:m0__RA10_01_2335:scan:604)

### Metabolights Repository Data

[mzspec:MTBLS38:(-)-epigallocatechin:scan:2](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MTBLS38:(-)-epigallocatechin:scan:2)
[mzspec:MSV000082791:(-)-epigallocatechin:scan:2](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000082791:(-)-epigallocatechin:scan:2)

### Metabolomics Workbench Repository Data

[mzspec:ST000003:iPSC-T1R1:scan:3](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:ST000003:iPSC-T1R1:scan:3)
[mzspec:MSV000082680:iPSC-T1R1:scan:3](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000082680:iPSC-T1R1:scan:3)

## Additional arguments for plotting views

mz_min: minimum mz value
mz_max: maximum mz value
annotate_peaks: include 'annotate_peaks' if you want the plot to label peaks that have intensity >50% of the biggest peak within [mz_min,mz_max]

e.g. 
[mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555&mz_min=400&mz_max=500&annotate_peaks)

## Deprecated Material

Test URLs for GNPS plotting:

task c95481f0c53d42e78a61bf899e9f9adb
file spectra/specs_ms.mgf
scan 1943

#Spectrum in Molecular Networking
https://metabolomics-usi.ucsd.edu/spectrum/?task=c95481f0c53d42e78a61bf899e9f9adb&file=spectra/specs_ms.mgf&scan=1943

#QRCode
https://metabolomics-usi.ucsd.edu/qrcode?task=c95481f0c53d42e78a61bf899e9f9adb&file=spectra/specs_ms.mgf&scan=1943

# Example for ms2lda
https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzdata:MS2LDATASK-38:blah:document:43062
Note the 38 is the experiment id, 43062 is the document id. blah can be anything!

#Test for GNPS Library Spectrum

