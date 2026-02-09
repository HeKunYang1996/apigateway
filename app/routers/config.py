"""
配置导出API路由
处理系统配置的导出功能
"""

import logging
import os
import zipfile
import tempfile
import shutil
import subprocess
import asyncio
import stat
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["配置管理"])

# 当前升级进程
current_upgrade_process = None
current_upgrade_file = None

# 升级相关目录（使用持久化路径，容器删除后仍存在）
UPGRADE_DIR = Path("/opt/MonarchEdge/upgrade")
UPGRADE_LOG_FILE = UPGRADE_DIR / "upgrade.log"

# 确保目录存在
UPGRADE_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/export", response_class=FileResponse)
async def export_config():
    """
    导出配置文件
    
    从 /opt/MonarchEdge/data 目录导出配置文件
    如果目录不存在，则返回失败消息
    """
    try:
        config_dir = Path("/opt/MonarchEdge/data")
        
        # 检查目录是否存在
        if not config_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "配置目录不存在",
                    "path": str(config_dir)
                }
            )
        
        # 检查目录是否为空
        if not any(config_dir.iterdir()):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "配置目录为空",
                    "path": str(config_dir)
                }
            )
        
        # 创建临时zip文件
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.zip', 
            prefix='config_export_'
        )
        temp_file.close()
        
        try:
            # 压缩配置目录
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历目录中的所有文件
                for root, dirs, files in os.walk(config_dir):
                    for file in files:
                        file_path = Path(root) / file
                        # 计算相对路径
                        arcname = file_path.relative_to(config_dir)
                        zipf.write(file_path, arcname)
                        logger.info(f"添加文件到压缩包: {arcname}")
            
            # 检查生成的zip文件大小
            zip_size = os.path.getsize(temp_file.name)
            logger.info(f"配置导出成功，压缩包大小: {zip_size} 字节")
            
            # 返回文件
            return FileResponse(
                path=temp_file.name,
                filename="monarchedge_config_export.zip",
                media_type="application/zip",
                background=None  # 不在后台删除，让操作系统处理临时文件
            )
            
        except Exception as e:
            # 如果出错，删除临时文件
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出配置异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"导出配置失败: {str(e)}"
            }
        )


@router.get("/check", response_model=Dict[str, Any])
async def check_config_dir():
    """
    检查配置目录状态
    
    检查 /opt/MonarchEdge/data 目录是否存在以及其中的文件数量
    """
    try:
        config_dir = Path("/opt/MonarchEdge/data")
        
        exists = config_dir.exists()
        is_dir = config_dir.is_dir() if exists else False
        
        file_count = 0
        total_size = 0
        
        if exists and is_dir:
            try:
                # 统计文件数量和总大小
                for root, dirs, files in os.walk(config_dir):
                    file_count += len(files)
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            total_size += file_path.stat().st_size
                        except Exception as e:
                            logger.warning(f"无法获取文件大小: {file_path}, 错误: {e}")
            except Exception as e:
                logger.error(f"遍历配置目录异常: {e}")
        
        return {
            "success": True,
            "message": "配置目录检查完成",
            "data": {
                "path": str(config_dir),
                "exists": exists,
                "is_directory": is_dir,
                "file_count": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        }
        
    except Exception as e:
        logger.error(f"检查配置目录异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"检查配置目录失败: {str(e)}"
            }
        )


@router.post("/import", response_model=Dict[str, Any])
async def import_config(file: UploadFile = File(...)):
    """
    导入配置文件
    
    上传ZIP压缩包，解压到 /opt/MonarchEdge/data 目录
    存在同名文件则覆盖
    """
    config_dir = Path("/opt/MonarchEdge/data")
    temp_zip_path = None
    temp_extract_dir = None
    
    try:
        # 验证文件类型
        if not file.filename.endswith('.zip'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "只支持ZIP格式的压缩文件"
                }
            )
        
        # 验证文件大小（限制为100MB）
        max_size = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "上传的文件为空"
                }
            )
        
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"文件大小超过限制（最大100MB），当前文件大小: {round(file_size / (1024 * 1024), 2)}MB"
                }
            )
        
        logger.info(f"开始导入配置，文件名: {file.filename}, 大小: {round(file_size / (1024 * 1024), 2)}MB")
        
        # 创建临时文件保存上传的ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip', prefix='config_import_') as temp_zip:
            temp_zip.write(file_content)
            temp_zip_path = temp_zip.name
        
        # 验证ZIP文件完整性
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # 测试ZIP文件完整性
                bad_file = zip_ref.testzip()
                if bad_file:
                    raise Exception(f"ZIP文件损坏，错误文件: {bad_file}")
                
                # 获取文件列表
                file_list = zip_ref.namelist()
                if not file_list:
                    raise Exception("ZIP文件中没有文件")
                
                logger.info(f"ZIP文件验证通过，包含 {len(file_list)} 个文件")
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "无效的ZIP文件格式"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"ZIP文件验证失败: {str(e)}"
                }
            )
        
        # 创建临时解压目录
        temp_extract_dir = tempfile.mkdtemp(prefix='config_extract_')
        
        # 解压到临时目录
        extracted_files: List[str] = []
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                # 跳过目录
                if file_info.is_dir():
                    continue
                
                # 安全检查：防止路径遍历攻击
                file_path = Path(file_info.filename)
                if file_path.is_absolute() or '..' in file_path.parts:
                    logger.warning(f"跳过不安全的文件路径: {file_info.filename}")
                    continue
                
                # 解压文件
                zip_ref.extract(file_info, temp_extract_dir)
                extracted_files.append(file_info.filename)
                logger.info(f"解压文件: {file_info.filename}")
        
        if not extracted_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "ZIP文件中没有有效的文件"
                }
            )
        
        # 确保目标目录存在
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制文件到目标目录（覆盖已存在的文件）
        imported_files: List[str] = []
        overwritten_files: List[str] = []
        new_files: List[str] = []
        
        for rel_path in extracted_files:
            src_file = Path(temp_extract_dir) / rel_path
            dest_file = config_dir / rel_path
            
            # 创建目标文件的父目录
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查文件是否已存在
            existed = dest_file.exists()
            
            # 复制文件（覆盖）
            shutil.copy2(src_file, dest_file)
            
            imported_files.append(rel_path)
            if existed:
                overwritten_files.append(rel_path)
                logger.info(f"覆盖文件: {rel_path}")
            else:
                new_files.append(rel_path)
                logger.info(f"新增文件: {rel_path}")
        
        logger.info(f"配置导入成功，共 {len(imported_files)} 个文件（新增: {len(new_files)}, 覆盖: {len(overwritten_files)}）")
        
        return {
            "success": True,
            "message": "配置导入成功",
            "data": {
                "total_files": len(imported_files),
                "new_files": len(new_files),
                "overwritten_files": len(overwritten_files),
                "target_directory": str(config_dir),
                "files": {
                    "new": new_files,
                    "overwritten": overwritten_files
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入配置异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"导入配置失败: {str(e)}"
            }
        )
    finally:
        # 清理临时文件
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.unlink(temp_zip_path)
                logger.info(f"已删除临时ZIP文件: {temp_zip_path}")
            except Exception as e:
                logger.warning(f"删除临时ZIP文件失败: {e}")
        
        if temp_extract_dir and os.path.exists(temp_extract_dir):
            try:
                shutil.rmtree(temp_extract_dir)
                logger.info(f"已删除临时解压目录: {temp_extract_dir}")
            except Exception as e:
                logger.warning(f"删除临时解压目录失败: {e}")


@router.post("/upgrade", response_model=Dict[str, Any])
async def upload_and_run_upgrade(
    file: UploadFile = File(...),
    auto_answers: Optional[str] = None
):
    """
    上传升级包并自动运行
    
    上传 .run 文件，保存到持久化目录并立即执行
    
    参数:
    - file: .run 格式的升级包文件
    - auto_answers: 自动应答字符串（可选），多个答案用逗号分隔，如 "1,y,y"
    
    注意：
    1. 升级程序会在后台独立进程中运行（使用nohup）
    2. 即使Docker容器被删除，升级进程也会继续运行
    3. 升级日志保存在持久化目录: /opt/MonarchEdge/upgrade/upgrade.log
    4. 建议将 /opt/MonarchEdge 挂载为Docker volume以保持数据持久化
    """
    global current_upgrade_process, current_upgrade_file
    
    try:
        # 检查是否已有升级在运行
        if current_upgrade_process is not None:
            try:
                # 检查进程是否还在运行
                current_upgrade_process.poll()
                if current_upgrade_process.returncode is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "success": False,
                            "message": "已有升级任务正在运行，请先中断或等待完成",
                            "current_file": current_upgrade_file,
                            "pid": current_upgrade_process.pid
                        }
                    )
            except:
                # 进程已结束，清除引用
                current_upgrade_process = None
                current_upgrade_file = None
        
        # 验证文件扩展名
        if not file.filename.endswith('.run'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "只支持 .run 格式的升级包文件"
                }
            )
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "上传的文件为空"
                }
            )
        
        # 限制文件大小（500MB）
        max_size = 500 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"文件大小超过限制（最大500MB），当前: {round(file_size / (1024 * 1024), 2)}MB"
                }
            )
        
        logger.info(f"收到升级包: {file.filename}, 大小: {round(file_size / (1024 * 1024), 2)}MB")
        
        # 保存升级包到持久化目录
        upgrade_file_path = UPGRADE_DIR / "upgrade_package.run"
        with open(upgrade_file_path, 'wb') as f:
            f.write(file_content)
        
        # 添加执行权限
        os.chmod(upgrade_file_path, 0o755)
        logger.info(f"升级包已保存: {upgrade_file_path}")
        
        # 准备自动应答
        answers_list = []
        if auto_answers:
            answers_list = [ans.strip() for ans in auto_answers.split(',')]
            logger.info(f"自动应答: {answers_list}")
        
        # 清空之前的日志文件
        with open(UPGRADE_LOG_FILE, 'w') as log_f:
            log_f.write(f"=== 升级开始时间: {datetime.now().isoformat()} ===\n")
            log_f.write(f"升级包: {file.filename}\n")
            log_f.write(f"文件大小: {round(file_size / (1024 * 1024), 2)}MB\n")
            log_f.write(f"自动应答: {answers_list}\n")
            log_f.write("=" * 60 + "\n\n")
        
        # 准备启动脚本（使用nohup让进程完全独立）
        # 这样即使Docker容器被删除，进程也会继续在宿主机运行
        start_script = UPGRADE_DIR / "start_upgrade.sh"
        with open(start_script, 'w') as f:
            f.write("#!/bin/bash\n\n")
            f.write(f"cd {UPGRADE_DIR}\n")
            f.write(f"echo '开始执行升级程序...' >> {UPGRADE_LOG_FILE}\n")
            
            # 如果有自动应答，通过管道传入
            if answers_list:
                answers_str = "\\n".join(answers_list)
                f.write(f"printf '{answers_str}\\n' | {upgrade_file_path} >> {UPGRADE_LOG_FILE} 2>&1\n")
            else:
                f.write(f"{upgrade_file_path} >> {UPGRADE_LOG_FILE} 2>&1\n")
            
            f.write(f"echo '' >> {UPGRADE_LOG_FILE}\n")
            f.write(f"echo '=== 升级结束时间: '$(date -Iseconds)' ===' >> {UPGRADE_LOG_FILE}\n")
            f.write(f"echo '退出码: '$? >> {UPGRADE_LOG_FILE}\n")
        
        os.chmod(start_script, 0o755)
        
        # 使用subprocess.Popen启动独立进程（完全后台运行）
        # 使用nohup确保进程不受容器删除影响
        process = subprocess.Popen(
            ['nohup', str(start_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # 创建新的会话，完全脱离当前进程
            cwd=str(UPGRADE_DIR)
        )
        
        current_upgrade_process = process
        current_upgrade_file = file.filename
        
        logger.info(f"升级程序已启动，PID: {process.pid}")
        logger.warning("⚠️ 注意：升级过程可能会删除Docker容器，请确保 /opt/MonarchEdge 已挂载为volume")
        
        return {
            "success": True,
            "message": "升级程序已启动",
            "data": {
                "filename": file.filename,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "pid": process.pid,
                "log_file": str(UPGRADE_LOG_FILE),
                "auto_answers": answers_list,
                "warning": "升级过程可能会重启或删除Docker容器，这是正常现象",
                "note": "可以通过查看日志文件或使用中断接口来监控/停止升级"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传并运行升级包异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"上传并运行升级包失败: {str(e)}"
            }
        )


@router.post("/upgrade/abort", response_model=Dict[str, Any])
async def abort_upgrade():
    """
    中断升级程序
    
    终止正在运行的升级进程
    
    注意：如果升级程序已经开始删除容器，中断可能无法完全停止升级过程
    """
    global current_upgrade_process, current_upgrade_file
    
    try:
        if current_upgrade_process is None:
            return {
                "success": False,
                "message": "没有正在运行的升级任务"
            }
        
        # 检查进程状态
        current_upgrade_process.poll()
        if current_upgrade_process.returncode is not None:
            # 进程已结束
            result = {
                "success": True,
                "message": f"升级程序已结束，退出码: {current_upgrade_process.returncode}",
                "data": {
                    "filename": current_upgrade_file,
                    "exit_code": current_upgrade_process.returncode,
                    "log_file": str(UPGRADE_LOG_FILE)
                }
            }
            current_upgrade_process = None
            current_upgrade_file = None
            return result
        
        # 进程还在运行，尝试终止
        pid = current_upgrade_process.pid
        filename = current_upgrade_file
        
        logger.info(f"尝试终止升级进程，PID: {pid}")
        
        # 记录到日志
        with open(UPGRADE_LOG_FILE, 'a') as log_f:
            log_f.write(f"\n\n!!! 升级被用户中断 ({datetime.now().isoformat()}) !!!\n")
        
        # 先尝试优雅终止（SIGTERM）
        try:
            current_upgrade_process.terminate()
            # 等待3秒看是否结束
            try:
                current_upgrade_process.wait(timeout=3)
                logger.info(f"升级进程已优雅终止，PID: {pid}")
            except subprocess.TimeoutExpired:
                # 3秒后还没结束，强制杀死（SIGKILL）
                logger.warning(f"升级进程未响应SIGTERM，强制杀死，PID: {pid}")
                current_upgrade_process.kill()
                current_upgrade_process.wait(timeout=5)
                logger.info(f"升级进程已强制终止，PID: {pid}")
        except Exception as e:
            logger.error(f"终止升级进程失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "message": f"终止升级进程失败: {str(e)}"
                }
            )
        
        result = {
            "success": True,
            "message": "升级程序已中断",
            "data": {
                "filename": filename,
                "pid": pid,
                "log_file": str(UPGRADE_LOG_FILE),
                "note": "请检查日志文件了解升级进度"
            }
        }
        
        current_upgrade_process = None
        current_upgrade_file = None
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"中断升级异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"中断升级失败: {str(e)}"
            }
        )


@router.get("/upgrade/status", response_model=Dict[str, Any])
async def get_upgrade_status():
    """
    获取升级状态
    
    返回当前升级任务的状态和最新日志
    """
    global current_upgrade_process, current_upgrade_file
    
    try:
        # 读取日志文件（最后50行）
        log_preview = ""
        if UPGRADE_LOG_FILE.exists():
            try:
                with open(UPGRADE_LOG_FILE, 'r') as f:
                    lines = f.readlines()
                    log_preview = "".join(lines[-50:])
            except Exception as e:
                logger.warning(f"读取日志文件失败: {e}")
                log_preview = f"无法读取日志文件: {str(e)}"
        else:
            log_preview = "日志文件不存在"
        
        # 检查进程状态
        if current_upgrade_process is None:
            return {
                "success": True,
                "message": "没有正在运行的升级任务",
                "data": {
                    "status": "idle",
                    "log_file": str(UPGRADE_LOG_FILE),
                    "log_preview": log_preview
                }
            }
        
        # 检查进程是否还在运行
        current_upgrade_process.poll()
        if current_upgrade_process.returncode is None:
            # 进程还在运行
            return {
                "success": True,
                "message": "升级任务正在运行",
                "data": {
                    "status": "running",
                    "filename": current_upgrade_file,
                    "pid": current_upgrade_process.pid,
                    "log_file": str(UPGRADE_LOG_FILE),
                    "log_preview": log_preview
                }
            }
        else:
            # 进程已结束
            exit_code = current_upgrade_process.returncode
            filename = current_upgrade_file
            
            # 清除全局引用
            current_upgrade_process = None
            current_upgrade_file = None
            
            return {
                "success": True,
                "message": f"升级任务已完成，退出码: {exit_code}",
                "data": {
                    "status": "completed" if exit_code == 0 else "failed",
                    "filename": filename,
                    "exit_code": exit_code,
                    "log_file": str(UPGRADE_LOG_FILE),
                    "log_preview": log_preview
                }
            }
        
    except Exception as e:
        logger.error(f"获取升级状态异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"获取升级状态失败: {str(e)}"
            }
        )


@router.get("/upgrade/log", response_class=FileResponse)
async def download_upgrade_log():
    """
    下载升级日志文件
    
    下载完整的升级日志
    """
    try:
        if not UPGRADE_LOG_FILE.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "日志文件不存在"
                }
            )
        
        return FileResponse(
            path=str(UPGRADE_LOG_FILE),
            filename="upgrade.log",
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载升级日志异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"下载升级日志失败: {str(e)}"
            }
        )
