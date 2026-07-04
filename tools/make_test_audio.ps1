# 테스트용 TTS(음성 합성) 오디오 생성 스크립트 (docs/validation-plan.md)
# 사용법:
#   powershell -ExecutionPolicy Bypass -File tools/make_test_audio.ps1
#   powershell ... -Text "원하는 문장" -OutFile out/이름.wav [-Culture en-US]
# - 기본: 한국어 보이스(ko-KR)가 있으면 한국어 기본 문장, 없으면 영어 기본 문장.
# - "정답 문장"이 콘솔에 출력되며, STT 결과 검증에 사용한다.
# - 생성물은 커밋하지 않는다(재생성 가능, .gitignore 대상).
param(
    [string]$OutDir = "out",
    [string]$Text = "",
    [string]$OutFile = "",
    [string]$Culture = ""
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $synth.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo }

# 보이스 선택: -Culture 지정 시 해당 문화권, 아니면 ko-KR 우선, 없으면 기본 보이스
$targetCulture = $Culture
if (-not $targetCulture) { $targetCulture = "ko-KR" }
$voice = $voices | Where-Object { $_.Culture.Name -eq $targetCulture } | Select-Object -First 1
if ($voice) {
    $synth.SelectVoice($voice.Name)
} elseif ($Culture) {
    Write-Host "[경고] '$Culture' 보이스가 없어 기본 보이스를 사용합니다."
}
$voiceName = $synth.Voice.Name
$langTag = $synth.Voice.Culture.TwoLetterISOLanguageName

# 문장: -Text 지정 시 그대로, 아니면 언어별 기본 문장
$sentence = $Text
if (-not $sentence) {
    if ($langTag -eq "ko") {
        $sentence = "안녕하세요. 오늘은 날씨가 맑고 화창합니다. 이 프로그램은 음성을 텍스트로 변환합니다."
    } else {
        $sentence = "Hello. Today the weather is clear and sunny. This program converts speech into text."
    }
}

# 출력 경로: -OutFile 지정 시 그대로, 아니면 OutDir/test_<언어>.wav
$wavPath = $OutFile
if (-not $wavPath) { $wavPath = Join-Path $OutDir ("test_{0}.wav" -f $langTag) }
$parentDir = Split-Path -Parent $wavPath
if ($parentDir -and -not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
}

$synth.SetOutputToWaveFile($wavPath)
$synth.Speak($sentence)
$synth.SetOutputToNull()
$synth.Dispose()

Write-Host "생성: $wavPath"
Write-Host "보이스: $voiceName / 언어: $langTag"
Write-Host "정답 문장: $sentence"
