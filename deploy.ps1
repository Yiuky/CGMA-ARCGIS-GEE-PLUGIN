$addinSrc = "arcgis_addin\GEE_Image_Selector.esriaddin"
$addinDest = "C:\Users\joberthgambati\Documents\ArcGIS\AddIns\Desktop10.8\{ceae58c4-c44e-4edd-b8f4-1ba7d13b6b7d}\GEE_Image_Selector.esriaddin"
$cacheDir = "C:\Users\joberthgambati\AppData\Local\ESRI\Desktop10.8\AssemblyCache\{CEAE58C4-C44E-4EDD-B8F4-1BA7D13B6B7D}"

Copy-Item $addinSrc $addinDest -Force
Copy-Item "arcgis_addin\Install\*" $cacheDir -Recurse -Force
Get-ChildItem -Path $cacheDir -Filter "*.pyc" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue

$found = Get-Content "$cacheDir\gee_gui.py" | Select-String "v1.5"
Write-Output "Found in cache: $found"

# Verify pure group template in cache
$p = "$cacheDir\empty_group_template.lyr"
$len = (Get-Item $p).Length
Write-Output "empty_group_template.lyr size: $len bytes"

Write-Output "DEPLOY_COMPLETE_V15"
