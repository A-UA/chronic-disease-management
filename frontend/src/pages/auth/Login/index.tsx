import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import { message } from 'antd';
import { login } from '@/services/api/auth';

export default () => {
  const { setInitialState } = useModel('@@initialState');

  const handleSubmit = async (values: any) => {
    try {
      const result = await login(values.username, values.password);
      localStorage.setItem('token', result.access_token);
      message.success('Login successful');

      // Re-fetch initial state
      const { getCurrentUser } = await import('@/services/api/auth');
      const currentUser = await getCurrentUser();
      setInitialState({ currentUser });

      history.push('/org/dashboard');
      return true;
    } catch (error: any) {
      message.error('Login failed, please check your credentials');
      return false;
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'white',
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <LoginForm
        title="Chronic Disease Admin"
        subTitle="Multi-Tenant AI SaaS Management"
        onFinish={handleSubmit}
      >
        <ProFormText
          name="username"
          fieldProps={{ size: 'large', prefix: <></> }}
          placeholder="Email"
          rules={[{ required: true, message: 'Please enter your email' }]}
        />
        <ProFormText.Password
          name="password"
          fieldProps={{ size: 'large', prefix: <></> }}
          placeholder="Password"
          rules={[{ required: true, message: 'Please enter your password' }]}
        />
      </LoginForm>
    </div>
  );
};
