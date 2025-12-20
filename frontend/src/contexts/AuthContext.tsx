/**
 * 认证上下文模块
 * 
 * 功能说明：
 *   提供全局的用户认证状态管理。
 *   统一使用玻尔平台认证（通过后端 /init-from-bohrium 接口）。
 * 
 * 认证流程：
 *   1. 组件挂载时调用后端接口初始化用户
 *   2. 成功 → 设置 user 状态
 *   3. 失败 → 设置 error 状态，显示错误页面
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { PaymentAPI } from '../services/api';

// ===================== 类型定义 =====================

/** 简化的用户信息类型（从玻尔平台获取） */
interface BohriumUser {
  id: string;
  name?: string;
  email?: string;
}

/** 认证上下文类型 */
interface AuthContextType {
  /** 当前用户信息 */
  user: BohriumUser | null;
  /** 是否正在加载 */
  loading: boolean;
  /** 认证错误信息 */
  error: string | null;
}

// ===================== 上下文创建 =====================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ===================== 本地存储键 =====================

const STORAGE_KEY = 'arxivscout_user';

// ===================== Provider 组件 =====================

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 尝试从 localStorage 恢复用户（快速渲染）
  const getCachedUser = (): BohriumUser | null => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        return JSON.parse(cached);
      }
    } catch {
      // 忽略解析错误
    }
    return null;
  };

  const [user, setUser] = useState<BohriumUser | null>(getCachedUser());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /**
     * 初始化用户认证
     * 
     * 流程：
     *   1. 调用后端 /init-from-bohrium 接口
     *   2. 后端从 Cookie 获取 accessKey 并验证
     *   3. 返回用户画像或错误
     */
    const initAuth = async () => {
      console.log('[Auth] 开始初始化用户认证...');
      
      try {
        const profile = await PaymentAPI.initFromBohrium();
        
        if (profile?.info?.id) {
          const userData: BohriumUser = {
            id: profile.info.id,
            name: profile.info.name,
            email: profile.info.email,
          };
          
          // 存储到 localStorage（持久化）
          localStorage.setItem(STORAGE_KEY, JSON.stringify(userData));
          
          setUser(userData);
          setError(null);
          console.log('[Auth] ✅ 用户认证成功:', userData.id);
        } else {
          throw new Error('返回数据格式异常');
        }
      } catch (err: any) {
        console.error('[Auth] ❌ 用户认证失败:', err);
        
        // 清除可能无效的缓存
        localStorage.removeItem(STORAGE_KEY);
        
        setUser(null);
        setError('获取您的信息失败，请刷新重试');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const value: AuthContextType = {
    user,
    loading,
    error,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// ===================== Hook 导出 =====================

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth 必须在 AuthProvider 内部使用');
  }
  return context;
};
