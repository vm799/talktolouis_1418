// Shared sample data for db/seed.ts.
//
// Pure data, no driver code, no I/O. Matches what each agent runtime
// previously seeded individually. To customize the starter's demo data,
// edit this file — both runtimes will see the changes after `pnpm db:seed`.

export interface UserSeed {
  user_id: string;
  name: string;
  email: string;
  preferences: { language: string; timezone: string };
}

export interface OrderSeed {
  user_id: string;
  order_id: string;
  items: string[];
  total: number;
  status: 'delivered' | 'pending' | 'shipped' | 'cancelled';
}

export interface KnowledgeSeed {
  title: string;
  content: string;
  category: string;
}

export const USERS: UserSeed[] = [
  {
    user_id: 'user_1',
    name: 'Jordan',
    email: 'jordan@example.com',
    preferences: { language: 'en', timezone: 'America/New_York' },
  },
  {
    user_id: 'user_2',
    name: 'Casey',
    email: 'casey@example.com',
    preferences: { language: 'en', timezone: 'Europe/London' },
  },
];

export const ORDERS: OrderSeed[] = [
  {
    user_id: 'user_1',
    order_id: 'order_1001',
    items: ['Widget A', 'Widget B'],
    total: 49.99,
    status: 'delivered',
  },
  {
    user_id: 'user_1',
    order_id: 'order_1002',
    items: ['Gadget X'],
    total: 29.99,
    status: 'pending',
  },
];

export const KNOWLEDGE_INPUTS: KnowledgeSeed[] = [
  {
    title: 'Handling interruptions',
    content:
      'Voice agents detect speech during a reply and pause playback. ' +
      'Use disallow_interruptions inside function tools that mutate state.',
    category: 'voice-agents',
  },
  {
    title: 'Session telemetry and metrics',
    content:
      'Use session.usage to collect per-model usage metrics. ' +
      'Export from on_session_end alongside the session report.',
    category: 'deployment',
  },
  {
    title: 'Choosing an STT provider',
    content:
      'LiveKit Inference supports Deepgram Nova-3, AssemblyAI, and ' +
      'others. Prefer models with built-in endpointing for realtime.',
    category: 'models',
  },
  {
    title: 'Voice agent RAG pattern',
    content:
      'Run vector search inside on_user_turn_completed and inject ' +
      'results into the chat context before the LLM replies.',
    category: 'patterns',
  },
  {
    title: 'Agentic memory pattern',
    content:
      'Expose remember, recall, forget, and search_memory as tools ' +
      'so the LLM decides what persists across sessions.',
    category: 'patterns',
  },
];
