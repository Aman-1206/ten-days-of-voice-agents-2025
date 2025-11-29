import { type VariantProps } from 'class-variance-authority';
import { Track } from 'livekit-client';
import { MicrophoneIcon } from '@phosphor-icons/react/dist/ssr';
import { AgentControlBar } from '@/components/livekit/agent-control-bar/agent-control-bar';
import { TrackDeviceSelect } from '@/components/livekit/agent-control-bar/track-device-select';
import { TrackSelector } from '@/components/livekit/agent-control-bar/track-selector';
import { TrackToggle } from '@/components/livekit/agent-control-bar/track-toggle';
import { Alert, AlertDescription, AlertTitle, alertVariants } from '@/components/livekit/alert';
import { AlertToast } from '@/components/livekit/alert-toast';
import { Button, buttonVariants } from '@/components/livekit/button';
import { ChatEntry } from '@/components/livekit/chat-entry';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/livekit/select';
import { ShimmerText } from '@/components/livekit/shimmer-text';
import { Toggle, toggleVariants } from '@/components/livekit/toggle';
import { cn } from '@/lib/utils';

type toggleVariantsType = VariantProps<typeof toggleVariants>['variant'];
type toggleVariantsSizeType = VariantProps<typeof toggleVariants>['size'];
type buttonVariantsType = VariantProps<typeof buttonVariants>['variant'];
type buttonVariantsSizeType = VariantProps<typeof buttonVariants>['size'];
type alertVariantsType = VariantProps<typeof alertVariants>['variant'];

interface ContainerProps {
  componentName?: string;
  children: React.ReactNode;
  className?: string;
}

function Container({ componentName, children, className }: ContainerProps) {
  return (
    <div className={cn('space-y-4 backdrop-blur-sm', className)}>
      <h3 className="text-foreground text-2xl font-bold text-red-200 drop-shadow-[0_0_6px_rgba(255,0,0,0.4)]">
        <span className="tracking-tight">{componentName}</span>
      </h3>

      {/* THEME UPDATE: Dark gothic card */}
      <div className="
        bg-[rgba(10,10,10,0.7)]
        border border-red-900/40 
        rounded-3xl 
        p-8 
        drop-shadow-[0_0_20px_rgba(100,0,0,0.35)]
        backdrop-blur-xl
      ">
        {children}
      </div>
    </div>
  );
}

function StoryTitle({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-red-300/60 mb-2 font-mono text-xs uppercase tracking-wider">
      {children}
    </h4>
  );
}

export default function Base() {
  return (
    <div
      className="
        relative 
        min-h-screen 
        py-10 
        text-red-100
        bg-[url('/dark_forest_bg.png')] 
        bg-cover 
        bg-center
      "
    >
      {/* Fog overlay */}
      <div className="absolute inset-0 bg-[url('/fog_overlay.png')] opacity-30 mix-blend-screen pointer-events-none animate-pulse"></div>

      <h2 className="mt-40 mb-8 text-4xl font-extralight tracking-tight text-red-100 drop-shadow-[0_0_10px_rgba(255,0,0,0.4)]">
        Primitives
      </h2>

      {/* Button */}
      <Container componentName="Button">
        <table className="w-full text-red-200">
          <thead className="font-mono text-xs font-normal uppercase [&_th]:w-1/5 [&_th]:p-2 [&_th]:text-center text-red-300/70">
            <tr>
              <th></th>
              <th>Small</th>
              <th>Default</th>
              <th>Large</th>
              <th>Icon</th>
            </tr>
          </thead>
          <tbody className="[&_td]:p-2 [&_td:not(:first-child)]:text-center text-red-100">
            {['default', 'primary', 'secondary', 'outline', 'ghost', 'link', 'destructive'].map(
              (variant) => (
                <tr key={variant}>
                  <td className="text-right font-mono text-xs uppercase text-red-300">
                    {variant}
                  </td>
                  {['sm', 'default', 'lg', 'icon'].map((size) => (
                    <td key={size}>
                      <Button
                        variant={variant as buttonVariantsType}
                        size={size as buttonVariantsSizeType}
                        className="hover:bg-red-900/40 transition-all shadow-[0_0_6px_rgba(255,0,0,0.4)]"
                      >
                        {size === 'icon' ? <MicrophoneIcon size={16} weight="bold" /> : 'Button'}
                      </Button>
                    </td>
                  ))}
                </tr>
              )
            )}
          </tbody>
        </table>
      </Container>

      {/* Toggle */}
      <Container componentName="Toggle">
        <table className="w-full text-red-200">
          <thead className="font-mono text-xs uppercase [&_th]:p-2 text-red-300/70 text-center">
            <tr>
              <th></th>
              <th>Small</th>
              <th>Default</th>
              <th>Large</th>
              <th>Icon</th>
            </tr>
          </thead>
          <tbody className="[&_td]:p-2 text-red-100 text-center">
            {['default', 'primary', 'secondary', 'outline'].map((variant) => (
              <tr key={variant}>
                <td className="text-right font-mono text-xs uppercase text-red-300">
                  {variant}
                </td>
                {['sm', 'default', 'lg', 'icon'].map((size) => (
                  <td key={size}>
                    <Toggle
                      size={size as toggleVariantsSizeType}
                      variant={variant as toggleVariantsType}
                      className="hover:bg-red-900/40 shadow-[0_0_8px_rgba(255,0,0,0.3)]"
                    >
                      {size === 'icon' ? <MicrophoneIcon size={16} weight="bold" /> : 'Toggle'}
                    </Toggle>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Container>

      {/* Alerts */}
      <Container componentName="Alert">
        {['default', 'destructive'].map((variant) => (
          <div key={variant}>
            <StoryTitle>{variant}</StoryTitle>
            <Alert
              key={variant}
              variant={variant as alertVariantsType}
              className="
                bg-red-900/20 
                border-red-800/50 
                text-red-200 
                shadow-[0_0_10px_rgba(255,0,0,0.25)]
              "
            >
              <AlertTitle>Alert {variant} title</AlertTitle>
              <AlertDescription>This is a {variant} alert description.</AlertDescription>
            </Alert>
          </div>
        ))}
      </Container>

      {/* Select */}
      <Container componentName="Select">
        <div className="grid w-full grid-cols-2 gap-2 text-red-200">
          <div>
            <StoryTitle>Size default</StoryTitle>
            <Select>
              <SelectTrigger className="bg-red-950/40 border-red-800 text-red-100">
                <SelectValue placeholder="Select a track" />
              </SelectTrigger>
              <SelectContent className="bg-red-950 border-red-800 text-red-100">
                <SelectItem value="1">Track 1</SelectItem>
                <SelectItem value="2">Track 2</SelectItem>
                <SelectItem value="3">Track 3</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <StoryTitle>Size sm</StoryTitle>
            <Select>
              <SelectTrigger className="bg-red-950/40 border-red-800 text-red-100" size="sm">
                <SelectValue placeholder="Select a track" />
              </SelectTrigger>
              <SelectContent className="bg-red-950 border-red-800 text-red-100">
                <SelectItem value="1">Track 1</SelectItem>
                <SelectItem value="2">Track 2</SelectItem>
                <SelectItem value="3">Track 3</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Container>

      {/* Other components — styling preserved but themed */}
      <h2 className="mt-40 mb-4 text-4xl font-extralight tracking-tight text-red-100 drop-shadow-[0_0_10px_rgba(255,0,0,0.4)]">
        Components
      </h2>

      {/* Agent control bar */}
      <Container componentName="AgentControlBar">
        <div className="relative flex items-center justify-center">
          <AgentControlBar
            className="w-full text-red-200 bg-red-950/30 border-red-800/40 shadow-[0_0_12px_rgba(255,0,0,0.3)]"
            controls={{
              leave: true,
              chat: true,
              camera: true,
              microphone: true,
              screenShare: true,
            }}
          />
        </div>
      </Container>

      {/* Rest UI untouched but themed */}
      <Container componentName="TrackDeviceSelect">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <StoryTitle>Size default</StoryTitle>
            <TrackDeviceSelect kind="audioinput" />
          </div>
          <div>
            <StoryTitle>Size sm</StoryTitle>
            <TrackDeviceSelect size="sm" kind="audioinput" />
          </div>
        </div>
      </Container>

      <Container componentName="TrackToggle">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <StoryTitle>Track.Source.Microphone</StoryTitle>
            <TrackToggle variant="outline" source={Track.Source.Microphone} />
          </div>
          <div>
            <StoryTitle>Track.Source.Camera</StoryTitle>
            <TrackToggle variant="outline" source={Track.Source.Camera} />
          </div>
        </div>
      </Container>

      <Container componentName="TrackSelector">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <StoryTitle>Track.Source.Camera</StoryTitle>
            <TrackSelector kind="videoinput" source={Track.Source.Camera} />
          </div>
          <div>
            <StoryTitle>Track.Source.Microphone</StoryTitle>
            <TrackSelector kind="audioinput" source={Track.Source.Microphone} />
          </div>
        </div>
      </Container>

      <Container componentName="ChatEntry">
        <div className="mx-auto max-w-prose space-y-4">
          <ChatEntry
            locale="en-US"
            timestamp={Date.now() + 1000}
            message="Hello, how are you?"
            messageOrigin="local"
            name="User"
          />
          <ChatEntry
            locale="en-US"
            timestamp={Date.now() + 5000}
            message="I am good, how about you?"
            messageOrigin="remote"
            name="Agent"
          />
        </div>
      </Container>

      <Container componentName="ShimmerText">
        <div className="text-center">
          <ShimmerText className="text-red-200 drop-shadow-[0_0_10px_rgba(255,0,0,0.4)]">
            This is shimmer text
          </ShimmerText>
        </div>
      </Container>

      <Container componentName="AlertToast">
        <StoryTitle>Alert toast</StoryTitle>
        <div className="mx-auto max-w-prose">
          <AlertToast
            id="alert-toast"
            title="Alert toast"
            description="This is a alert toast description."
          />
        </div>
      </Container>
    </div>
  );
}
