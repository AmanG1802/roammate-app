import { EntitlementProvider } from '@/hooks/useEntitlement';
import { TutorialProvider } from '@/hooks/useTutorial';
import TutorialDriver from '@/components/tutorial/TutorialProvider';
import { PaywallModal } from '@/components/billing/PaywallModal';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <EntitlementProvider>
      <TutorialProvider>
        {children}
        <PaywallModal />
        <TutorialDriver />
      </TutorialProvider>
    </EntitlementProvider>
  );
}
