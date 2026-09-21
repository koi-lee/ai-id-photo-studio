# AI ID Photo Studio — AI 증명사진 워크플로

[简体中文](README.md) · [English](README.md#english) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · 한국어

AI를 활용한 의상·헤어스타일·배경 변경 미리보기와 Python 기반 로컬 이미지 처리를 결합한 오픈 소스 Agent 스킬입니다. 독립적인 온라인 증명사진 서비스는 아닙니다.

## 주요 기능

- 이미지 생성 서비스를 이용한 의상, 헤어스타일, 배경 변경 미리보기.
- 커플 사진 스타일 예시: 흰 셔츠, 검은 정장, 회색 정장, 중국풍 의상, 파란색과 흰색 셔츠.
- 로컬 자르기, 크기 조절 및 여러 출력 크기 지원.
- 얼굴 형태의 부분 조정 도구와 화질·변경 영역 점검 절차.

![AI 모델로 만든 커플 사진 예시](examples/couple/couple-white-shirts-red-preview.png)

[다섯 가지 예시와 제한 사항](examples/couple/README.md)(중국어). 예시는 AI로 생성한 모델이며 실제 부부의 사진이 아닙니다. 커플 예시는 내장 이미지 생성 도구로 제작했으며, 저장소 스크립트의 생성 성능을 검증한 결과가 아닙니다.

## 지원 범위

주로 중국에서 사용하는 사진 크기 프리셋을 제공합니다. **한국 여권, 주민등록증 등 개별 증명사진 규정에 대한 적합성은 검증하지 않았습니다.** 한국어 문서가 있다고 해서 한국 공식 규격을 지원하는 것은 아닙니다.

본인과의 유사성이나 제출 기관의 승인을 보장하지 않습니다. 공식 제출 시 해당 기관의 최신 요건을 확인하세요. 합성 커플 사진은 스타일 미리보기용입니다.

## 로컬 실행

Python 3.10 이상을 준비하고 저장소 루트에서 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python skill/scripts/process_id_photo.py examples/male/base-portrait.jpg --spec 1inch --outdir output/demo --no-watermark
```

Windows에서는 `.venv\Scripts\activate`로 활성화합니다. 이 예시는 기존 이미지의 후처리이며 AI 의상 변경을 실행하지 않습니다.

Agent에서 사용하려면 `skill/` 폴더 전체를 해당 Agent의 스킬 디렉터리에 복사하세요. [실행 예시](docs/usage-examples.md)와 [스킬 본문](skill/SKILL.md)은 중국어입니다.

## 비용과 개인정보

코드는 [MIT 라이선스](LICENSE)로 제공됩니다. 이미지 생성 서비스는 별도 비용이 발생할 수 있습니다. 로컬 후처리는 이미지를 외부로 보내지 않지만 원격 생성 서비스를 선택하면 입력 이미지가 해당 서비스로 전송됩니다. 본인이나 가족의 사진 및 파생 이미지를 공개 저장소에 올리지 마세요.

이 페이지는 개요와 시작 방법의 번역입니다. 전체 문서 번역이나 한국어 UI를 제공한다는 뜻은 아닙니다.
