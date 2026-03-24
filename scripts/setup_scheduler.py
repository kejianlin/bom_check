#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
设置定时同步任务
支持Windows任务计划程序和Linux cron
"""

import sys
import os
import platform
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_default_logger

logger = get_default_logger()


def setup_windows_task():
    """设置Windows任务计划"""
    project_path = Path(__file__).parent.parent.absolute()
    python_exe = sys.executable
    script_path = project_path / "sync" / "plm_sync.py"
    
    task_name = "PLM_Data_Sync"
    
    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>PLM数据自动同步任务</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T02:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path}" --mode incremental</Arguments>
      <WorkingDirectory>{project_path}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
    
    xml_file = project_path / "scripts" / "task_schedule.xml"
    with open(xml_file, 'w', encoding='utf-16') as f:
        f.write(task_xml)
    
    print("\n" + "="*80)
    print("Windows任务计划配置")
    print("="*80)
    print(f"任务名称: {task_name}")
    print(f"执行时间: 每天凌晨2:00")
    print(f"Python路径: {python_exe}")
    print(f"脚本路径: {script_path}")
    print(f"工作目录: {project_path}")
    print("\n请手动执行以下命令创建任务计划:")
    print(f'  schtasks /Create /TN "{task_name}" /XML "{xml_file}"')
    print("\n或者通过任务计划程序GUI手动创建:")
    print("  1. 打开任务计划程序 (taskschd.msc)")
    print("  2. 创建任务")
    print("  3. 触发器：每天凌晨2:00")
    print(f"  4. 操作：启动程序 {python_exe}")
    print(f"     参数: \"{script_path}\" --mode incremental")
    print(f"     起始于: {project_path}")
    print("="*80)


def setup_linux_cron():
    """设置Linux cron任务"""
    project_path = Path(__file__).parent.parent.absolute()
    python_exe = sys.executable
    script_path = project_path / "sync" / "plm_sync.py"
    
    cron_line = f"0 2 * * * cd {project_path} && {python_exe} {script_path} --mode incremental >> {project_path}/logs/sync_cron.log 2>&1"
    
    print("\n" + "="*80)
    print("Linux Cron任务配置")
    print("="*80)
    print("请执行以下命令编辑crontab:")
    print("  crontab -e")
    print("\n添加以下行:")
    print(f"  {cron_line}")
    print("\n或者使用命令直接添加:")
    print(f"  (crontab -l 2>/dev/null; echo \"{cron_line}\") | crontab -")
    print("="*80)


def main_setup():
    """主函数"""
    logger.info("定时任务设置向导")
    
    system = platform.system()
    
    if system == "Windows":
        setup_windows_task()
    elif system in ["Linux", "Darwin"]:
        setup_linux_cron()
    else:
        logger.error(f"不支持的操作系统: {system}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main_setup())
