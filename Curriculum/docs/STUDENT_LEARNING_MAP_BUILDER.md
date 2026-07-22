# Student Learning Map Builder

The Student Learning Map Builder is a local Windows application for creating customized one- or two-page student learning maps. It does not require a browser or installation.

## For teachers

1. Open the `Student Learning Map Builder` folder and double-click `Student Learning Map Builder.exe`.
2. Choose a course and select an official unit under **Start from unit**.
3. Select **Start new map from selected unit** to load that unit's objectives and title.
4. To blend units or add an extension topic, choose a different unit under **Add from unit or extension**. Select **Add entire unit**, or select individual objectives and choose **Add selected objectives**.
5. Remove or reorder objectives as needed and edit the map title.
6. Choose an output action:
   - **Save PDF** asks where to save the file.
   - **Save & Open** saves it in the displayed output folder and opens it.
   - **Print to default** saves a copy and sends it to the Windows default printer after confirmation.

Generated PDFs are saved in `Documents\Student Learning Maps` by default. Use **Change folder** if a different location is preferred.

The builder never edits the official curriculum. It uses the approved objective wording, supporting skills, and I/D/A/R tags packaged with the application.

## Shared Google Drive distribution

Place the complete `Student Learning Map Builder` folder in a faculty-only shared Google Drive. Teachers may open it from a locally synced Google Drive folder or copy the complete folder to their computer. The `_internal` folder must remain beside the executable.

Replace the complete application folder in Google Drive when a curriculum update is packaged.

The executable is not digitally signed. If institutional security software blocks it, ask IT to approve or sign the application rather than bypassing the warning.

## Mac compatibility

The packaged `.exe` is Windows-only and will not open on macOS. The application source and PDF engine are designed to be cross-platform, but a separate macOS application must be packaged on a Mac. macOS may also require institutional signing or notarization before wider distribution.

## For curriculum maintainers

The packaged application contains a snapshot of the course and skill-progression data at build time. Repackage it after curriculum changes:

```powershell
./tools/package_unit_learning_map_builder.ps1 -PythonExecutable "path-to-python.exe"
```

The selected Python environment must contain ReportLab, pypdf, and PyInstaller. The finished distribution is written to `output/apps/student-learning-map-builder/`.
