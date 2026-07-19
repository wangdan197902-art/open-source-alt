---
title: "Slack"
vendor: "Salesforce"
category: "team-communication"
openSourceAlternative: "Element"
license: "AGPL-3.0"
aiGenerated: true
reviewStatus: "approved"
description: "Slack의 오픈소스 대안: Element"
---

# Slack → Element

## 소프트웨어 정보
- 상용 소프트웨어: Slack
- 오픈소스 대안: Element
- 공급업체: Salesforce
- 라이선스: AGPL-3.0 (Matrix 프로토콜 기반)

## 기능 비교
| 기능 | Slack | Element |
|------|-------|---------|
| 채널 | ✅ | ✅ |
| 다이렉트 메시지 | ✅ | ✅ |
| 스레드 | ✅ | ✅ |
| 종단 간 암호화 | ⚠️ 엔터프라이즈만 | ✅ 기본 활성화 |
| 셀프 호스팅 | ❌ | ✅ |
| 음성/비디오 통화 | ✅ | ✅ |
| 봇 및 연동 | ✅ | ✅ |

## 장점
- 분산형 프로토콜 (Matrix)
- 기본 종단 간 암호화
- 셀프 호스팅으로 데이터 완전 주권
- 서버 간 연합 통신

## 단점
- Slack만큼 세련된 UX는 아님
- 연동 마켓이 작음
- 셀프 호스팅 시 서버 운영 필요

## 마이그레이션 난이도
**중간** — 채널 구조는 직접 매핑 가능하지만 Slack 전용 앱과 워크플로는 Matrix 봇과 브리지로 교체해야 합니다. 사용자는 연합 식별 모델에 적응해야 합니다.
