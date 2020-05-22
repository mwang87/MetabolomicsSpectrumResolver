# USI Resolver and Displayer for Metabolomics

This tool is meant to be able to show summarize USI's from various sources. It will achieve the following goals

1. Enable creation of embeddable images in publications that will link out to viewable/interactable spectrum plots
1. 3rd party embedding for visualization of spectra that exist in reposities (e.g. MassIVE, PRIDE, PeptideAtlas)
1. 3rd party embedding of qrcode

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

[mzspec:MASSBANK:SM858102](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzdata:MASSBANK:SM858102)

### ProteoXchange Repository Data

[mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)

### MassIVE/GNPS Repository Data

[mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)

[mzspec:MSV000078547:120228_nbut_3610_it_it_take2:scan:389](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzdata:MSV000078547:120228_nbut_3610_it_it_take2:scan:389)

We can also render MS1 MS/MS spectra from MassIVE/GNPS

[mzspec:MSV000085444:Hui_N3_fe:scan:500](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000085444:Hui_N3_fe:scan:500)

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


## USI Extended for Metabolomics - Formatting Documentation

### Massbank Library Spectrum

```mzspec:MASSBANK:<Massbank Accession>```

### GNPS Analysis Task Spectrum

```mzspec:GNPSTASK-<GNPS Task ID>:<File name in task>:scan:<scan number>```

### MS2LDA MOTIFDB

```mzspec:MOTIFDB:motif:<Motif DB accession>```

### GNPS Library Spectrum

```mzspec:GNPSLIBRARY:<GNPS Library Accession>```

### Metabolights Data Repository Spectrum

```mzspec:<Metabolights Accession>:<Filename>:scan:<Scan Number>```

### Metabolomics Workbench Data Repository Spectrum

```mzspec:<Metabolomics Workbench Accession>:<Filename>:scan:<Scan Number>```

### MassIVE/GNPS Data Repository Spectrum

[See Proteomics USI Standard](http://www.psidev.info/usi)

## Example Formatting Figures

Vanilla Rendering
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943)

Small Figure
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943&width=4&height=4&mz_min=&mz_max=&max_intensity=&grid=true&annotate_threshold=0&annotate_precision=2&annotation_rotation=70)

Mass Range Filtering
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943&width=10&height=6&mz_min=550&mz_max=800&max_intensity=&grid=true&annotate_threshold=5&annotate_precision=4&annotation_rotation=90)

Less Decimal Places
![](https://metabolomics-usi.ucsd.edu/png/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943&width=10&height=6&mz_min=&mz_max=&max_intensity=&grid=true&annotate_precision=1&annotation_rotation=90)

Rotate Labels
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943&width=10&height=6&mz_min=&mz_max=&max_intensity=&grid=true&annotate_peaks=true&annotate_threshold=5&annotate_precision=2&annotation_rotation=70)

Decreate Label Minimum Intensity
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943&width=10&height=6&mz_min=&mz_max=&max_intensity=&grid=true&annotate_threshold=0&annotate_precision=2&annotation_rotation=70)

No Grid
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943&width=10&height=6&mz_min=&mz_max=&max_intensity=&grid=false&annotate_threshold=5&annotate_precision=4&annotation_rotation=90)

Vanilla Mirror Match
![](https://metabolomics-usi.ucsd.edu/svg/mirror?usi1=mzspec:MASSBANK:BSU00002&usi2=mzdata:MASSBANK:BSU00002)

Mirror Match with Intensity Scaling
![](https://metabolomics-usi.ucsd.edu/svg/mirror?usi1=mzdata:MASSBANK:BSU00002&usi2=mzspec:MASSBANK:BSU00002&width=10&height=6&mz_min=&mz_max=&max_intensity=150&grid=true&annotate_threshold=5&annotate_precision=4&annotation_rotation=90)

## Plotting Parameters

annotate_peaks - this url parameter defines which peaks in which spectrum (top or bottom) will be annotated. The parameters is a list of peaks to be annotated. It is a list of strings, where each string indicates whether to annotate a peak. Each string, is encoded by ```spectrum-index```. ```spectrum``` is either 0 (top) or 1 (bottom) and ```index``` is the index of the peak (0 indexed). 

## URL Endpoints

1. /png/
1. /svg/
1. /json/
1. /api/proxi/v0.1/spectra
1. /csv/
1. /qrcode/
1. /spectrum/
1. /mirror/
1. /svg/mirror
1. /png/mirror
