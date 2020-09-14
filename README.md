# USI Resolver and Displayer for Metabolomics

This tool is meant to be able to show USIs from various sources. It will achieve the following goals:

1. Enable creation of embeddable images in publications that will link out to viewable/interactable spectrum plots.
2. 3rd party embedding for visualization of spectra that exist in repositories (e.g. MassIVE, PRIDE, PeptideAtlas).
3. 3rd party embedding of QR code.

Supported USI Types:

1. GNPS Molecular Networking Clustered Spectra
2. GNPS Spectral Libraries
3. ProteoXchange Repository Data
4. MS2LDA Reference Motifs
5. MassBank Library Spectra
6. MetaboLights Dataset Spectra
7. Metabolomics Workbench Dataset Spectra

![unittest](https://github.com/mwang87/MetabolomicsSpectrumResolver/workflows/unittest/badge.svg)
![loadtest](https://github.com/mwang87/MetabolomicsSpectrumResolver/workflows/loadtest/badge.svg)

> :warning: These identifiers are based on draft USI and draft Metabolomics USI identifiers. 
        Thus, they are subject to change, and so for the moment, they will be specified as `mzdraft` instead of `mzspec` in the first block. 
        Thank you for your patience and working with us!

## Example USI URLs

### MS2LDA

[mzspec:MS2LDA:TASK-190:accession:43062](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MS2LDA:TASK-190:accession:43062)

### MOTIFDB

[mzspec:MOTIFDB::accession:171163](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MOTIFDB::accession:171163)

### GNPS Molecular Networking Spectra

[mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943)

### GNPS Library Spectra

[mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077)

### MassBank Library Spectra

[mzspec:MASSBANK::accession:SM858102](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MASSBANK::accession:SM858102)

### ProteomeXchange Repository Data

[mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)

### MassIVE/GNPS Repository Data

[mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555)

[mzspec:MSV000078547:120228_nbut_3610_it_it_take2:scan:389](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzdata:MSV000078547:120228_nbut_3610_it_it_take2:scan:389)

#### MassIVE/GNPS MS1 Spectra

[mzspec:MSV000085444:Hui_N3_fe:scan:500](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000085444:Hui_N3_fe:scan:500)

### MetaboLights Repository Data

[mzspec:MSV000082791:(-)-epigallocatechin:scan:2](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000082791:(-)-epigallocatechin:scan:2)

### Metabolomics Workbench Repository Data

[mzspec:MSV000082680:iPSC-T1R1:scan:3](https://metabolomics-usi.ucsd.edu/spectrum/?usi=mzspec:MSV000082680:iPSC-T1R1:scan:3)


## USI Extended for Metabolomics - Formatting Documentation

### Massbank Library Spectrum

```mzspec:MASSBANK::accession:<MassBank Accession>```

### GNPS Analysis Task Spectrum

```mzspec:GNPS:TASK-<GNPS Task ID>-<File name in task>:scan:<scan number>```

### MS2LDA MOTIFDB

```mzspec:MOTIFDB::accession:<Motif DB accession>```

### GNPS Library Spectrum

```mzspec:GNPS:<GNPS library name (ignored)>:accession:<GNPS Library Accession>```

### Metabolights Data Repository Spectrum

```mzspec:<MetaboLights MSV identifier>:<Filename>:scan:<Scan Number>```

### Metabolomics Workbench Data Repository Spectrum

```mzspec:<Metabolomics Workbench MSV identifier>:<Filename>:scan:<Scan Number>```

### MassIVE/GNPS Data Repository Spectrum

[See Proteomics USI Standard](http://www.psidev.info/usi)


## Example Formatting Figures

Vanilla Rendering
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943)

Small Figure
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&width=4&height=4)

Mass Range Filtering
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&mz_min=550&mz_max=800)

Zoom Intensity
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&max_intensity=50)

No Grid
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&grid=false)

No Peak Annotations
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&annotate_peaks=[[]])

Custom Peak Annotations
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&annotate_peaks=[[463.297,708.463,816.474,1042.5699]])

Less Decimal Places
![](https://metabolomics-usi.ucsd.edu/png/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&annotate_precision=1)

Rotate Labels
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&annotation_rotation=45)

Decrease Label Minimum Intensity
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&annotate_threshold=0)

Vanilla Mirror Match
![](https://metabolomics-usi.ucsd.edu/svg/mirror?usi1=mzspec:MASSBANK::accession:BSU00002&usi2=mzspec:MASSBANK::accession:BSU00002)

Mirror Match with Intensity Scaling
![](https://metabolomics-usi.ucsd.edu/svg/mirror?usi1=mzspec:MASSBANK::accession:BSU00002&usi2=mzspec:MASSBANK::accession:BSU00002&max_intensity=150)

Custom Title
![](https://metabolomics-usi.ucsd.edu/svg/?usi=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&plot_title=CUSTOMTITLE)

## Plotting Parameters

- `mz_min`: Minimum m/z value.
- `mz_max`: Maximum m/z value.
- `annotate_peaks`: Defines which peaks in which spectrum (top or bottom) will be annotated. The parameters is a list of lists of m/z values of the peaks to be annotated. For a single spectrum plot it should be a single nested list (i.e. `[[m1, m2]]`), for a mirror plot it should be two nested lists for the top spectrum and the bottom spectrum (i.e. `[[s1m1,s1m2],[s2m1,s2m2]]`).
- `plot_title`: Custom plot title, omit to use default

## URL Endpoints

1. /png/
1. /svg/
1. /json/
1. /proxi/v0.1/spectra
1. /csv/
1. /qrcode/
1. /spectrum/
1. /mirror/
1. /svg/mirror
1. /png/mirror
