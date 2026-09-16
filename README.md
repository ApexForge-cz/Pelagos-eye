# Pelagos-eye
 3D global maritime situational visualization platform with AIS and ocean environment data

Pelagos-eye 是一个面向海事研究的三维空间可视化Web平台。系统集成AIS船舶轨迹、港口基础信息、海洋气象、地震事件等多源空间数据，基于FastAPI + CesiumJS 构建数字地球态势大屏，支持空间数据查询、指标统计与异常告警。

> ⚠️ This project is for learning and research purposes only, NOT for real navigation or maritime law enforcement.

## Tech Stack
- Backend: Python, FastAPI, Pydantic, PostGIS, Redis, Polars
- Frontend: React + TypeScript, CesiumJS, ECharts
- DevOps: Docker, Pytest

## Features
- 🌐 3D Digital Earth visualization powered by Cesium
- 🚢 AIS vessel position & historical playback
- ⚓ Port information inquiry
- 🌊 Ocean weather & environmental monitoring
- 📊 Data statistics dashboard and alert system

## License
MIT
