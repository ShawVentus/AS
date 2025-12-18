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
  React.useEffect(() => {
    if (stepIndex === 0 && run) {
      // 检查步骤2的目标元素是否存在
      const interval = setInterval(() => {
        const step2Target = document.querySelector('[data-tour="manual-query-input"]');
        if (step2Target) {
          console.log('[引导气泡] 检测到Modal已打开，自动进入步骤2');
          setStepIndex(1);
          clearInterval(interval);
        }
      }, 100); // 每100ms检查一次
      
      // 5秒后清理
      const timeout = setTimeout(() => {
        clearInterval(interval);
      }, 5000);
      
      return () => {
        clearInterval(interval);
        clearTimeout(timeout);
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
      content: '💡 报告生成组件 - 立即体验。点击这里开始生成您的第一份报告！',
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
      content: '💡 填写信息 + AI 润色。输入您的研究兴趣，可以使用 AI 智能填充优化描述。',
      placement: 'bottom',
      disableBeacon: true,
      spotlightClicks: true, // 允许操作表单
      hideBackButton: true, // 隐藏"上一步"按钮
      disableOverlayClose: true, // 禁止点击遮罩层关闭
      styles: {
        options: {
          zIndex: 10000,
        },
      },
    },
    {
      // 步骤3：指向"保存为默认设置"按钮
      // 只允许点击"完成"按钮，不允许返回，但允许跳过
      target: '[data-tour="save-default-checkbox"]',
      content: '💡 保存 - 作为报告生成根据。勾选保存，下次生成时将自动使用此配置。',
      placement: 'top',
      disableBeacon: true,
      spotlightClicks: true, // 允许操作表单
      hideBackButton: true, // 隐藏"上一步"按钮
      disableOverlayClose: true, // 禁止点击遮罩层关闭
      styles: {
        options: {
          zIndex: 10000,
        },
      },
    },
  ];

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
    
    // 打印调试信息（开发环境下方便排查问题）
    console.log('[引导气泡] 事件触发:', { 
      状态: status, 
      操作: action, 
      类型: type, 
      步骤: index 
    });
    
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
      setStepIndex(0); // 重置步骤索引
      onComplete();
    }
  };

  return (
    <Joyride
      steps={steps}
      run={run}
      stepIndex={stepIndex}  // 🆕 受控模式：手动控制当前步骤
      continuous // 连续模式，用户点击"下一步"自动进入下一步
      showSkipButton // 显示"跳过"按钮
      showProgress // 显示进度指示器 (1/3, 2/3, 3/3)
      callback={handleJoyrideCallback}
      disableOverlayClose={false} // 允许点击遮罩层关闭（步骤2/3）
      disableCloseOnEsc={false} // 允许 ESC 键关闭
      styles={{
        // 自定义样式，匹配系统深色主题
        options: {
          primaryColor: '#6366f1', // 主题色（Indigo-600）
          backgroundColor: '#1e293b', // 深色背景（Slate-800）
          textColor: '#f1f5f9', // 浅色文字（Slate-100）
          overlayColor: 'rgba(0, 0, 0, 0.7)', // 遮罩层颜色（70%透明度黑色）
          zIndex: 10000, // 确保在所有元素之上
        },
        tooltip: {
          borderRadius: 12, // 圆角
          fontSize: 14, // 字体大小
          padding: 20, // 内边距
        },
        tooltipContainer: {
          textAlign: 'left', // 文本左对齐
        },
        buttonNext: {
          backgroundColor: '#6366f1', // 下一步按钮背景色
          borderRadius: 8, // 按钮圆角
          padding: '8px 16px', // 按钮内边距
        },
        buttonBack: {
          color: '#94a3b8', // 上一步按钮文字颜色（Slate-400）
          marginRight: 10, // 右边距
        },
        buttonSkip: {
          color: '#94a3b8', // 跳过按钮文字颜色（Slate-400）
        },
        spotlight: {
          borderRadius: 8, // 高亮区域圆角
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
