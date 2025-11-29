'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import type { AppConfig } from '@/app-config';
import { ChatTranscript } from '@/components/app/chat-transcript';
import { PreConnectMessage } from '@/components/app/preconnect-message';
import { TileLayout } from '@/components/app/tile-layout';
import {
  AgentControlBar,
  type ControlBarControls,
} from '@/components/livekit/agent-control-bar/agent-control-bar';
import { useChatMessages } from '@/hooks/useChatMessages';
import { useConnectionTimeout } from '@/hooks/useConnectionTimout';
import { useDebugMode } from '@/hooks/useDebug';
import { cn } from '@/lib/utils';
import { ScrollArea } from '../livekit/scroll-area/scroll-area';

const MotionBottom = motion.create('div');

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';
const BOTTOM_VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1, translateY: '0%' },
    hidden: { opacity: 0, translateY: '100%' },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: { duration: 0.3, delay: 0.5, ease: 'easeOut' },
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'pointer-events-none h-4',
        top && 'bg-gradient-to-b from-black/80 to-transparent',
        bottom && 'bg-gradient-to-t from-black/80 to-transparent',
        className,
      )}
    />
  );
}

interface SessionViewProps {
  appConfig: AppConfig;
}

export const SessionView = ({
  appConfig,
  ...props
}: React.ComponentProps<'section'> & SessionViewProps) => {
  useConnectionTimeout(200_000);
  useDebugMode({ enabled: IN_DEVELOPMENT });

  const messages = useChatMessages();
  const [chatOpen, setChatOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const controls: ControlBarControls = {
    leave: true,
    microphone: true,
    chat: appConfig.supportsChatInput,
    camera: appConfig.supportsVideoInput,
    screenShare: appConfig.supportsVideoInput,
  };

  // auto-scroll on local messages
  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section
      className="
        relative z-10 h-full w-full overflow-hidden
        bg-[url('/dark_forest_bg.png')] bg-cover bg-center
        text-red-100
      "
      {...props}
    >
      {/* FOG OVERLAY */}
      <div
        className="
          absolute inset-0 
          bg-[url('/fog_overlay.png')]
          opacity-35 
          mix-blend-screen
          animate-pulse 
          pointer-events-none
          z-0
        "
      ></div>

      {/* CHAT TRANSCRIPT */}
      <div
        className={cn(
          'fixed inset-0 grid grid-cols-1 grid-rows-1 transition-all',
          !chatOpen && 'pointer-events-none opacity-0',
          chatOpen && 'opacity-100',
        )}
      >
        <Fade top className="absolute inset-x-4 top-0 h-40" />

        <ScrollArea
          ref={scrollAreaRef}
          className="
            px-4 pt-40 pb-[150px]
            md:px-6 md:pb-[180px]
            relative z-10
          "
        >
          <ChatTranscript
            hidden={!chatOpen}
            messages={messages}
            className="
              mx-auto max-w-2xl space-y-3 
              transition-opacity duration-300 ease-out
              text-red-100
              drop-shadow-[0_0_8px_rgba(255,0,0,0.4)]
            "
          />
        </ScrollArea>
      </div>

      {/* TILE LAYOUT (camera, avatar, waveform, etc.) */}
      <TileLayout chatOpen={chatOpen} />

      {/* BOTTOM CONTROL BAR */}
      <MotionBottom
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="
          fixed inset-x-3 bottom-0 z-50 md:inset-x-12
        "
      >
        {appConfig.isPreConnectBufferEnabled && (
          <PreConnectMessage
            messages={messages}
            className="
              pb-4 text-red-200 drop-shadow-[0_0_10px_rgba(255,0,0,0.5)]
            "
          />
        )}

        <div
          className="
            relative mx-auto max-w-2xl pb-3 md:pb-12
            bg-black/50 backdrop-blur-xl
            border border-red-900/40
            rounded-2xl
            shadow-[0_0_20px_rgba(255,0,0,0.35)]
          "
        >
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />

          <AgentControlBar
            controls={controls}
            onChatOpenChange={setChatOpen}
            className="
              text-red-200
              [&_*]:!text-red-200
            "
          />
        </div>
      </MotionBottom>
    </section>
  );
};
