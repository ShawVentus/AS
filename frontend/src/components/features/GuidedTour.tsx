/**
 * 产品引导气泡组件
 * 
 * 功能：为新用户提供三步引导教程，帮助用户快速了解报告生成功能
 * 
 * 使用场景：
 * - 用户首次登录时自动触发
 * - 检测到 userProfile.has_completed_tour === false 时显示
 * 
 * 引导流程：
 * 1. 步骤1：指向"立即生成报告"按钮，强制用户点击
 * 2. 步骤2：指向输入框，引导填写研究兴趣
 * 3. 步骤3：指向"保存为默认设置"，说明配置的作用
 * 
 * @example
 * <GuidedTour 
 *   run={showTour} 
 *   onComplete={handleComplete} 
 * />
 */

import React from 'react';
import Joyride, { STATUS, type CallBackProps, type Step } from 'react-joyride';

/**
 * GuidedTour 组件的属性接口
 */
interface GuidedTourProps {
  /** 是否运行引导（true 显示，false 隐藏） */
  run: boolean;
  /** 引导完成或跳过时的回调函数 */
  onComplete: () => void;
}

/**
 * 产品引导气泡组件
 * 
 * Args:
 *   run (boolean): 是否显示引导气泡
 *   onComplete (function): 引导完成或跳过时的回调函数
 * 
 * Returns:
 *   JSX.Element: 引导组件的 JSX 结构
 */
export const GuidedTour: React.FC<GuidedTourProps> = ({ run, onComplete }) => {
  
  // 受控模式：手动控制当前步骤索引
  const [stepIndex, setStepIndex] = React.useState(0);
  
  /**
   * 监听Modal打开，自动从步骤1切换到步骤2
   * 
   * 当用户点击"立即生成报告"按钮后，Modal会打开，
   * 此时步骤2的目标元素（输入框）会出现在DOM中。
   * 我们检测到目标元素后，自动切换到步骤2。
   */
  /**
   * 监听ManualReportPage打开，自动从步骤1切换到步骤2
   * 
   * 当用户点击"立即生成报告"按钮后，ManualReportPage会显示，
   * 此时步骤2的目标元素（输入框）会出现在DOM中。
   * 我们检测到目标元素后，自动切换到步骤2。
   */
  React.useEffect(() => {
    if (stepIndex === 0 && run) {
      console.log('[引导气泡] 开始检测步骤2目标元素...');
      let attemptCount = 0;
      
      // 检查步骤2的目标元素是否存在
      // 只要还在步骤1且引导正在运行，就一直检测，直到找到目标元素
      const interval = setInterval(() => {
        attemptCount++;
        const step2Target = document.querySelector('[data-tour="manual-query-input"]');
        
        // 降低日志频率：每50次打印一次（5秒一次）
        if (attemptCount % 50 === 0) {
             console.log(`[引导气泡] 正在等待步骤2目标元素... (已检测${attemptCount}次)`);
        }
        
        if (step2Target) {
          console.log('[引导气泡] ✅ 检测到ManualReportPage已打开，自动进入步骤2');
          setStepIndex(1);
          clearInterval(interval);
        }
      }, 100); // 每100ms检查一次
      
      return () => {
        clearInterval(interval);
      };
    }
  }, [stepIndex, run]);
  
  /**
   * 定义三个引导步骤
   * 
   * 步骤配置说明：
   * - target: CSS 选择器，定位目标元素（通过 data-tour 属性）
   * - content: 气泡提示内容
   * - placement: 气泡位置（top/bottom/left/right）
   * - disableBeacon: 禁用初始脉动点，直接显示气泡
   * - spotlightClicks: 是否允许点击高亮区域
   * - hideCloseButton: 是否隐藏关闭按钮
   * - disableOverlayClose: 是否禁止点击遮罩层关闭
   */
  const steps: Step[] = [
    {
      // 步骤1：指向"立即生成报告"按钮
      // 强制用户点击目标按钮，不能点击"下一步"或"跳过"
      target: '[data-tour="generate-report-btn"]',
      content: (
        <div style={{ fontSize: '1.3rem', fontWeight: 400 }}>
          👏🏻欢迎来到ArxivScout！点击这里开始生成您的第一份今日报告！
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      spotlightClicks: true, // 允许点击按钮
      hideFooter: true, // 隐藏底部按钮区域（"下一步"和"跳过"按钮）
      hideCloseButton: true, // 隐藏关闭按钮
      disableOverlayClose: true, // 禁止点击遮罩层关闭
      styles: {
        options: {
          zIndex: 10000, // 确保在最上层
        },
      },
    },
    {
      // 步骤2：指向输入框
      // 只允许点击"下一步"按钮，不允许返回，但允许跳过
      target: '[data-tour="manual-query-input"]',
      content: (
        <div style={{ fontSize: '1.1rem', lineHeight: 1.5 }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
            💡 输入偏好 + AI 智能填充
          </div>
          <div>输入您的研究兴趣，AI 将自动为您分析相关论文的所属类别。点击生成研报，Arxivscout会为您检索阅读相关类别下符合您需求的论文。</div>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      spotlightClicks: true, // 允许操作表单
      hideBackButton: true, // 隐藏"上一步"按钮
      disableOverlayClose: true, // 禁止点击遮罩层关闭
      styles: {
        options: {
          zIndex: 10000,
        },
        tooltip: {
          width: 450, // 增加气泡框宽度，使内容展示更舒适
        },
      },
    },
    {
      // 步骤3：指向"保存为默认设置"按钮
      // 只允许点击"完成"按钮，不允许返回，但允许跳过
      target: '[data-tour="save-default-checkbox"]',
      content: (
        <div style={{ fontSize: '1.1rem', lineHeight: 1.5 }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
            📌 保存为默认偏好
          </div>
          <div>将本次偏好保存为默认设置，即可作为每日研报偏好，自动为您检索分析相关论文。您也可在顶部设置页面中管理偏好。</div>
        </div>
      ),
      placement: 'top-start',
      floaterProps: {
        offset: 0, // 减小偏移，使气泡更贴近按钮
      },
      disableBeacon: true,
      spotlightClicks: true, // 允许操作表单
      hideBackButton: true, // 隐藏"上一步"按钮
      disableOverlayClose: true, // 禁止点击遮罩层关闭
      styles: {
        options: {
          zIndex: 10000,
        },
        tooltip: {
          width: 400, // 设置固定宽度有助于气泡框对齐
        },
      },
    },
  ];

  /**
   * 组件生命周期管理
   * 
   * 功能：
   * 1. 组件卸载时强制恢复页面滚动样式，防止样式残留导致页面死锁。
   * 2. 🆕 增加对内部滚动容器的精准清理。
   * 
   * Args:
   *   无
   * 
   * Returns:
   *   void
   */
  React.useEffect(() => {
    return () => {
      console.log('[引导气泡] 组件卸载，执行暴力样式清理...');
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
      
      // 🆕 精准清理内部滚动容器
      const container = document.getElementById('main-scroll-container');
      if (container) {
        container.style.overflow = '';
      }
    };
  }, []);

  /**
   * 监听 run 状态变化
   * 当引导开始时 (run=true)，重置步骤索引为 0
   * 
   * Args:
   *   run (boolean): 引导运行状态
   * 
   * Returns:
   *   void
   */
  React.useEffect(() => {
    if (run) {
      setStepIndex(0);
    }
  }, [run]);

  /**
   * 引导事件回调处理器
   * 
   * 处理引导过程中的各种事件，包括步骤切换、完成、跳过等。
   * 
   * Args:
   *   data (CallBackProps): react-joyride 的事件数据对象
   *     - status: 引导状态（finished/skipped/running等）
   *     - action: 用户操作（next/prev/skip/close等）
   *     - type: 事件类型（step:before/step:after/tour:end等）
   *     - index: 当前步骤索引
   * 
   * Returns:
   *   void
   */
  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, action, type, index } = data;
    
    // 处理步骤切换（用户点击"下一步"）
    if (action === 'next' && type === 'step:after') {
      setStepIndex(index + 1);
    }
    // 处理返回上一步
    else if (action === 'prev' && type === 'step:after') {
      setStepIndex(index - 1);
    }
    
    // 引导完成或跳过时触发回调
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      const statusText = status === STATUS.FINISHED ? '已完成' : '已跳过';
      console.log(`[引导气泡] 引导${statusText}`);
      
      // 🆕 立即清理样式 (第一道防线)
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
      const container = document.getElementById('main-scroll-container');
      if (container) container.style.overflow = '';
      
      onComplete();
    }
  };

  return (
    <Joyride
      steps={steps}
      run={run}
      stepIndex={stepIndex}
      continuous // 连续模式
      showSkipButton // 显示"跳过"按钮
      showProgress // 显示进度指示器
      callback={handleJoyrideCallback}
      disableOverlayClose={false}
      disableCloseOnEsc={false}
      disableScrolling={true} // 禁用 Joyride 的自动滚动接管
      disableScrollParentFix={true} // 🆕 禁用 Joyride 的滚动父级修复逻辑（防止其将容器设为 initial）
      styles={{
        // 自定义样式，匹配系统深色主题
        options: {
          primaryColor: '#6366f1', // 主题色
          backgroundColor: '#1e293b', // 深色背景
          textColor: '#f1f5f9', // 浅色文字
          overlayColor: 'rgba(0, 0, 0, 0.7)', // 遮罩层颜色
          zIndex: 10000, // 确保在最上层
        },
        tooltip: {
          borderRadius: 12,
          fontSize: 14,
          padding: 20,
        },
        tooltipContainer: {
          textAlign: 'left',
        },
        buttonNext: {
          backgroundColor: '#6366f1',
          borderRadius: 8,
          padding: '8px 16px',
        },
        buttonBack: {
          color: '#94a3b8',
          marginRight: 10,
        },
        buttonSkip: {
          color: '#94a3b8',
        },
        spotlight: {
          borderRadius: 8,
        },
      }}
      locale={{
        // 中文本地化
        back: '上一步',
        close: '关闭',
        last: '完成',
        next: '下一步',
        skip: '跳过',
      }}
    />
  );
};
