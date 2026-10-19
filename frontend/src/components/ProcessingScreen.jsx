import { useState, useEffect } from 'react'

const STEPS = [
  {
    id: 1,
    name: 'Extractor agent',
    desc: 'Finding all action items...',
    doneDesc: 'Action items extracted',
    duration: 4000,
  },
  {
    id: 2,
    name: 'Summarizer agent',
    desc: 'Writing meeting summary...',
    doneDesc: 'Summary complete',
    duration: 3500,
  },
  {
    id: 3,
    name: 'Email drafter agent',
    desc: 'Drafting follow-up email...',
    doneDesc: 'Email drafted',
    duration: 3000,
  },
]

function ProcessingScreen() {
  const [activeStep, setActiveStep] = useState(1)
  const [doneSteps, setDoneSteps] = useState([])

  useEffect(() => {
    let stepIndex = 0
    const runStep = () => {
      if (stepIndex >= STEPS.length) return
      const step = STEPS[stepIndex]
      setActiveStep(step.id)
      const timer = setTimeout(() => {
        setDoneSteps(prev => [...prev, step.id])
        stepIndex++
        if (stepIndex < STEPS.length) runStep()
      }, step.duration)
      return timer
    }
    const t = runStep()
    return () => clearTimeout(t)
  }, [])

  const progress = Math.round((doneSteps.length / STEPS.length) * 100)

  return (
    <div className="h-full flex items-center justify-center bg-slate-950 p-8">
      <div className="flex flex-col items-center gap-8 w-full max-w-sm">

        <div className="relative w-16 h-16 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-500 animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-indigo-300 animate-spin-slow" />
          <div className="w-8 h-8 bg-slate-800 rounded-full flex items-center justify-center text-indigo-400 text-base">
            ✦
          </div>
        </div>

        <div className="text-center">
          <h2 className="text-lg font-semibold text-slate-100">
            Analysing your meeting
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {STEPS.length} AI agents are working on your transcript
          </p>
        </div>

        <div className="w-full flex flex-col gap-3">
          {STEPS.map(step => {
            const isDone = doneSteps.includes(step.id)
            const isActive = activeStep === step.id && !isDone

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300 ${
                  isDone
                    ? 'bg-slate-800 border-slate-700'
                    : isActive
                    ? 'bg-slate-800 border-indigo-500'
                    : 'bg-slate-900 border-slate-800'
                }`}
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                  isDone
                    ? 'bg-green-500 text-white animate-step-done'
                    : isActive
                    ? 'bg-indigo-600 text-white animate-pulse-soft'
                    : 'bg-slate-700 text-slate-500'
                }`}>
                  {isDone ? '✓' : step.id}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${
                    isDone ? 'text-slate-400' : isActive ? 'text-slate-100' : 'text-slate-600'
                  }`}>
                    {step.name}
                  </p>
                  <p className={`text-xs mt-0.5 ${
                    isDone ? 'text-green-500' : isActive ? 'text-indigo-400' : 'text-slate-600'
                  }`}>
                    {isDone ? step.doneDesc : isActive ? step.desc : 'Waiting...'}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        <div className="w-full">
          <div className="flex justify-between text-xs text-slate-500 mb-2">
            <span>Step {Math.min(doneSteps.length + 1, STEPS.length)} of {STEPS.length}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

      </div>
    </div>
  )
}

export default ProcessingScreen