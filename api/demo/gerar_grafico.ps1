# Figura autoral para a aula de função afim. Não usa imagens externas.
Add-Type -AssemblyName System.Drawing
$canvas = New-Object System.Drawing.Bitmap(900, 560)
$drawing = [System.Drawing.Graphics]::FromImage($canvas)
$drawing.Clear([System.Drawing.Color]::White)
$drawing.SmoothingMode = 'AntiAlias'
$font = New-Object System.Drawing.Font('Arial', 15)
$pen = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 2)
$line = New-Object System.Drawing.Pen([System.Drawing.Color]::DarkBlue, 4)
$drawing.DrawString('Funcao afim: f(x) = 2x + 3', $font, [System.Drawing.Brushes]::Black, 220, 12)
$drawing.DrawLine($pen, 80, 480, 820, 480)
$drawing.DrawLine($pen, 80, 480, 80, 60)
for ($xValue=0; $xValue -le 6; $xValue++) {
 $screenX = 80 + $xValue*110
 $drawing.DrawString([string]$xValue,$font,[System.Drawing.Brushes]::Black,$screenX-5,485)
}
for ($yValue=0; $yValue -le 16; $yValue+=2) {
 $screenY = 480 - $yValue*25
 $drawing.DrawString([string]$yValue,$font,[System.Drawing.Brushes]::Black,35,$screenY-12)
}
$drawing.DrawString('x',$font,[System.Drawing.Brushes]::Black,830,475)
$drawing.DrawString('f(x)',$font,[System.Drawing.Brushes]::Black,50,35)
$drawing.DrawLine($line,80,405,740,105)
foreach ($xValue in @(1,3)) {
 $yValue=2*$xValue+3
 $screenX=80+$xValue*110
 $screenY=480-$yValue*25
 $drawing.FillEllipse([System.Drawing.Brushes]::DarkBlue,$screenX-6,$screenY-6,12,12)
 $drawing.DrawString("($xValue, $yValue)",$font,[System.Drawing.Brushes]::Black,$screenX+12,$screenY)
}
$canvas.Save((Join-Path $PSScriptRoot 'funcao_afim.png'),[System.Drawing.Imaging.ImageFormat]::Png)
$line.Dispose(); $pen.Dispose(); $font.Dispose(); $drawing.Dispose(); $canvas.Dispose()
