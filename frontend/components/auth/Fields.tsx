import { Mail, Lock, User as UserIcon } from 'lucide-react';

const inputCls =
  'block w-full pl-11 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium';

function Wrap({ Icon, children }: { Icon: any; children: React.ReactNode }) {
  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
        <Icon className="h-5 w-5 text-slate-400" />
      </div>
      {children}
    </div>
  );
}

export function NameField(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Wrap Icon={UserIcon}>
      <input type="text" placeholder="Full Name" required className={inputCls} {...props} />
    </Wrap>
  );
}

export function EmailField(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Wrap Icon={Mail}>
      <input type="email" placeholder="Email Address" required autoComplete="email" className={inputCls} {...props} />
    </Wrap>
  );
}

export function PasswordField(props: React.InputHTMLAttributes<HTMLInputElement> & { autoComplete?: string }) {
  return (
    <Wrap Icon={Lock}>
      <input
        type="password"
        placeholder="Password"
        required
        minLength={8}
        autoComplete={props.autoComplete ?? 'current-password'}
        className={inputCls}
        {...props}
      />
    </Wrap>
  );
}
