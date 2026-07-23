import VideoTemplate from './components/video/VideoTemplate'

function App() {
  return (
    <div className="w-full h-screen bg-black flex items-center justify-center">
      <div className="w-[1080px] h-[1920px] max-w-[56.25vh] max-h-screen relative overflow-hidden bg-deep-plum shadow-2xl">
        <VideoTemplate />
      </div>
    </div>
  )
}

export default App
