import React, { createContext, useContext, useEffect, useState } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '../services/supabase';
import { PaymentAPI } from '../services/api';

// 开发模式配置
const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';
const DEV_USER_ID = import.meta.env.VITE_DEV_USER_ID || '6z023dyl';

interface AuthContextType {
  session: Session | null;
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
  bohriumUserId: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 开发模式：初始化时直接使用固定 user_id
  const initialUser = DEV_MODE ? {
    id: DEV_USER_ID,
    email: 'dev@arxivscout.local',
    app_metadata: {},
    user_metadata: {},
    aud: 'authenticated',
    created_at: new Date().toISOString(),
  } as User : null;

  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(initialUser);
  const [loading, setLoading] = useState(!DEV_MODE);  // 开发模式不需要 loading
  const [bohriumUserId, setBohriumUserId] = useState<string | null>(DEV_MODE ? DEV_USER_ID : null);

  useEffect(() => {
    // 开发模式：尝试初始化玻尔用户（确保数据库中有该用户）
    if (DEV_MODE) {
      console.log('[Auth] 🔧 开发模式：使用固定 user_id =', DEV_USER_ID);
      PaymentAPI.initFromBohrium().then(profile => {
        console.log('[Auth] ✅ 玻尔用户初始化成功:', profile?.info?.id);
      }).catch(() => {
        console.log('[Auth] ⚠️ 玻尔初始化跳过（开发模式继续使用固定用户）');
      });
      return;
    }

    // 生产模式：使用 Supabase Auth
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // 初始化玻尔用户
    PaymentAPI.initFromBohrium().then(profile => {
      if (profile?.info?.id) {
        setBohriumUserId(profile.info.id);
      }
    }).catch(() => {});

    return () => subscription.unsubscribe();
  }, []);

  const signOut = async () => {
    if (DEV_MODE) {
      console.log('[Auth] 开发模式不支持登出');
      return;
    }
    await supabase.auth.signOut();
  };

  const value = {
    session,
    user,
    loading,
    signOut,
    bohriumUserId,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
