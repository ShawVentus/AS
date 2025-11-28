import React, { useState } from 'react';
import { supabase } from '../../services/supabase';

interface RegisterProps {
  onLoginClick: () => void;
}

export const Register: React.FC<RegisterProps> = ({ onLoginClick }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
      });

      if (error) throw error;
      setSuccess(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-lg p-8 shadow-xl text-center">
          <h2 className="text-2xl font-bold text-white mb-4">注册成功！</h2>
          <p className="text-slate-400 mb-6">
            请检查您的邮箱 ({email}) 并点击确认链接以激活账号。
          </p>
          <button
            onClick={onLoginClick}
            className="text-indigo-400 hover:text-indigo-300"
          >
            返回登录
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-lg p-8 shadow-xl">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">注册 Arxiv Scout</h2>
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              required
              minLength={6}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition-colors disabled:opacity-50"
          >
            {loading ? '注册中...' : '注册'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-500">
          已有账号？{' '}
          <button onClick={onLoginClick} className="text-indigo-400 hover:text-indigo-300">
            立即登录
          </button>
        </div>
      </div>
    </div>
  );
};
