# 테스트용 TTS(음성 합성) 오디오 생성 스크립트 (docs/validation-plan.md)
# 사용법: powershell -ExecutionPolicy Bypass -File tools/make_test_audio.ps1 [-OutDir out]
# - 한국어 보이스(ko-KR)가 있으면 한국어 문장, 없으면 영어 문장으로 WAV를 만든다.
# - "정답 문장"이 콘솔에 출력되며, STT 결과 검증에 사용한다.
# - 생성물은 커밋하지 않는다(재생성 가능, .gitignore 대상).
param(
    [string]$OutDir = "out"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

$voices = $synth.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo }
Write-Host "설치된 보이스:"
$voices | ForEach-Object { Write-Host ("  - {0} ({1})" -f $_.Name, $_.Culture) }

# 한국어 보이스 우선, 없으면 기본(영어) 보이스로 폴백
$koVoice = $voices | Where-Object { $_.Culture.Name -eq "ko-KR" } | Select-Object -First 1
if ($koVoice) {
    $sentence = "안녕하세요. 오늘은 날씨가 맑고 화창합니다. 이 프로그램은 음성을 텍스트로 변환합니다."
    $synth.SelectVoice($koVoice.Name)
    $langTag = "ko"
} else {
    $sentence = "Hello. Today the weather is clear and sunny. This program converts speech into text."
    $langTag = "en"
}

$wavPath = Join-Path $OutDir ("test_{0}.wav" -f $langTag)
$synth.SetOutputToWaveFile($wavPath)
$synth.Speak($sentence)
$synth.SetOutputToNull()
$synth.Dispose()

Write-Host ""
Write-Host "생성: $wavPath"
Write-Host "언어: $langTag"
Write-Host "정답 문장: $sentence"
