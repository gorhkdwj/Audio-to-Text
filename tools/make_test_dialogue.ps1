# 화자 구분(--diarize) 테스트용: 서로 다른 두 보이스를 한 WAV에 이어 붙인다.
# 사용법:
#   powershell -ExecutionPolicy Bypass -File tools/make_test_dialogue.ps1 [-OutFile out/test_dialogue.wav]
#   powershell ... -Voice1 "Microsoft David Desktop" -Voice2 "Microsoft Zira Desktop" `
#                  -Text1 "..." -Text2 "..." -Text3 "..."
# - 구성: 화자1(Text1) → 화자2(Text2) → 화자1(Text3). 사이에 0.6초 무음.
#   기대 결과: 첫 등장 순서 규칙(D-003)에 따라 Voice1=화자 1, Voice2=화자 2.
# - 참고: Whisper는 파일당 한 언어로 디코딩하므로, 화자 구분 검증용 픽스처는
#   두 화자가 같은 언어를 쓰는 구성이 적합하다(T-003/W-010 참조).
# - 생성물은 커밋하지 않는다(재생성 가능, .gitignore 대상).
param(
    [string]$OutFile = "out/test_dialogue.wav",
    [string]$Voice1 = "Microsoft Heami Desktop",
    [string]$Voice2 = "Microsoft Zira Desktop",
    [string]$Text1 = "안녕하세요. 첫 번째 화자입니다. 오늘 회의를 시작하겠습니다.",
    [string]$Text2 = "Hello, I am the second speaker. Thank you for joining today.",
    [string]$Text3 = "네, 반갑습니다. 이것으로 테스트를 마치겠습니다."
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$parentDir = Split-Path -Parent $OutFile
if ($parentDir -and -not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
}

$turns = @(
    @{ Voice = $Voice1; Text = $Text1 },
    @{ Voice = $Voice2; Text = $Text2 },
    @{ Voice = $Voice1; Text = $Text3 }
)

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile($OutFile)
foreach ($turn in $turns) {
    $synth.SelectVoice($turn.Voice)
    $synth.Speak($turn.Text)
    # 화자 사이 간격(0.6초 무음)
    $synth.SpeakSsml('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR"><break time="600ms"/></speak>')
}
$synth.SetOutputToNull()
$synth.Dispose()

Write-Host "생성: $OutFile"
Write-Host "구성(정답):"
foreach ($turn in $turns) {
    Write-Host ("  [{0}] {1}" -f $turn.Voice, $turn.Text)
}
