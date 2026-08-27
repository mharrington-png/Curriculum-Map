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

## USB and shared-drive distribution

Copy the complete `Student Learning Map Builder` folder. Teachers may open it from a USB drive or locally synced faculty-only shared drive, or copy the complete folder to their computer. The `_internal` folder must remain beside the executable.

Replace the complete application folder when a curriculum update is packaged.

Internally signed builds include `Student Learning Map Builder Publisher.cer`. Before distributing the app, ask IT to verify that certificate's thumbprint and deploy it to **Local Computer > Trusted Root Certification Authorities** on the intended Windows computers. This explicitly trusts software signed by the certificate, so IT should verify the thumbprint through a separate trusted channel and limit deployment to school-managed computers. The certificate is constrained to code signing and its private key remains non-exportable on the maintainer's computer. It does not establish public trust on arbitrary computers.

An administrator can install the verified public certificate on one computer with:

```powershell
Import-Certificate -FilePath ".\Student Learning Map Builder Publisher.cer" -CertStoreLocation Cert:\LocalMachine\Root
```

The executable's signature and certificate thumbprint can be checked with:

```powershell
Get-AuthenticodeSignature ".\Student Learning Map Builder.exe" | Format-List Status,StatusMessage,SignerCertificate
```

## Mac compatibility

The packaged `.exe` is Windows-only and will not open on macOS. The application source and PDF engine are designed to be cross-platform, but a separate macOS application must be packaged on a Mac. macOS may also require institutional signing or notarization before wider distribution.

## For curriculum maintainers

The packaged application contains a snapshot of the course and skill-progression data at build time. Repackage it after curriculum changes:

```powershell
./tools/package_unit_learning_map_builder.ps1 -PythonExecutable "path-to-python.exe" -Sign
```

The selected Python environment must contain ReportLab, pypdf, and PyInstaller. The first signed build creates a non-exportable self-signed certificate in the maintainer's Windows certificate store; later builds reuse it. The private key never enters the application folder. The finished distribution is written to `output/apps/student-learning-map-builder/`.
