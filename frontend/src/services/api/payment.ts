/**
 * 支付 API 客户端模块
 * 
 * 功能说明：
 *   封装与后端支付接口的通信，提供用户购买研报次数的功能。
 *   
 * 主要功能：
 *   - consume(): 购买研报生成次数
 *   - initFromBohrium(): 通过玻尔平台初始化用户
 */

import type { UserProfile } from '../../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';


// ===================== 类型定义 =====================

/**
 * 购买请求参数
 */
export interface ConsumeRequest {
  /** 消费的光子数量（100/400/1200） */
  eventValue: number;
  /** 购买的次数（1/5/20） */
  quotaAmount: number;
}

/**
 * 购买响应数据
 */
export interface ConsumeResponseData {
  /** 玻尔平台交易流水号 */
  outBizNo?: string;
  /** 玻尔平台请求 ID */
  requestId?: number;
  /** 更新后的次数余额 */
  newQuota?: number;
}

/**
 * 购买响应
 */
export interface ConsumeResponse {
  /** 是否购买成功 */
  success: boolean;
  /** 结果提示消息 */
  message: string;
  /** 购买成功时的详细数据 */
  data?: ConsumeResponseData;
}


// ===================== 价格档位配置 =====================

/**
 * 价格档位配置
 * 用于前端展示和参数验证
 */
export const PRICE_TIERS = [
  {
    name: '单次生成',
    eventValue: 100,
    quotaAmount: 1,
    pricePerUnit: 100,
    discount: null,
    recommended: false,
    hot: false,
  },
  {
    name: '购买一周研报',
    eventValue: 400,
    quotaAmount: 5,
    pricePerUnit: 80,
    discount: '20% OFF',
    recommended: true,
    hot: false,
  },
  {
    name: '购买一月研报',
    eventValue: 1200,
    quotaAmount: 20,
    pricePerUnit: 60,
    discount: '40% OFF',
    recommended: false,
    hot: true,
  },
] as const;

export type PriceTier = typeof PRICE_TIERS[number];


// ===================== 工具函数 =====================

/**
 * 通用 JSON 请求函数（支持 Cookie 传递）
 * 
 * 注意：使用 credentials: 'include' 确保 Cookie 被发送到后端
 */
async function fetchJSON<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    credentials: 'include', // 重要：确保 Cookie 被发送
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}


// ===================== API 函数 =====================

export const PaymentAPI = {
  /**
   * 购买研报生成次数
   * 
   * 调用后端 /api/payment/consume 接口，执行玻尔平台扣费。
   * 成功后用户的 remaining_quota 会自动增加。
   * 
   * @param params - 包含 eventValue（光子数）和 quotaAmount（次数）
   * @returns 购买结果
   * 
   * @example
   * const result = await PaymentAPI.consume({ eventValue: 400, quotaAmount: 5 });
   * if (result.success) {
   *   console.log('购买成功，新余额:', result.data?.newQuota);
   * }
   */
  consume: (params: ConsumeRequest): Promise<ConsumeResponse> => 
    fetchJSON<ConsumeResponse>('/payment/consume', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /**
   * 通过玻尔平台初始化用户
   * 
   * 调用后端 /api/user/init-from-bohrium 接口，
   * 自动从 Cookie 读取 accessKey 并创建/获取用户信息。
   * 
   * @returns 用户画像
   * 
   * @example
   * const profile = await PaymentAPI.initFromBohrium();
   * console.log('用户 ID:', profile.info.id);
   */
  initFromBohrium: (): Promise<UserProfile> =>
    fetchJSON<UserProfile>('/user/init-from-bohrium', {
      method: 'POST',
    }),
};

export default PaymentAPI;
