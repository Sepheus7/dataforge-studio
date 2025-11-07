/**
 * Main application page - routes to different views
 */

import { useAppStore } from '@/lib/store';
import ChatView from '@/components/views/ChatView';
import SchemaView from '@/components/views/SchemaView';
import JobsView from '@/components/views/JobsView';
import DownloadsView from '@/components/views/DownloadsView';
import SettingsView from '@/components/views/SettingsView';

export default function Home() {
  const currentView = useAppStore((state) => state.currentView);

  return (
    <>
      {currentView === 'chat' && <ChatView />}
      {currentView === 'schema' && <SchemaView />}
      {currentView === 'jobs' && <JobsView />}
      {currentView === 'downloads' && <DownloadsView />}
      {currentView === 'settings' && <SettingsView />}
    </>
  );
}

