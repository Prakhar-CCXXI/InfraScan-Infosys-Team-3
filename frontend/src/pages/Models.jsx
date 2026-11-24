import { useState } from 'react';
import { Cpu, CheckCircle, RefreshCw, Activity, Layers, Database } from 'lucide-react';
import { api } from '../services/api.js';
import { Card, PageHead, Stat, Badge } from '../components/ui.jsx';

export default function Models() {
  const [models, setModels] = useState(() => api.getModels());
  const [activeTab, setActiveTab] = useState('all');

  const deployedCount = models.filter((m) => m.status === 'Deployed').length;
  const testingCount = models.filter((m) => m.status === 'Testing').length;

  const toggleStatus = (id) => {
    const updated = api.toggleModelStatus(id);
    setModels([...updated]);
  };

  const filtered = activeTab === 'all' ? models : models.filter((m) => m.status.toLowerCase() === activeTab);

  return (
    <>
      <PageHead
        title="AI Model Management"
        sub="Inspection AI inference engines, segmentation benchmarks and production deployment status"
      >
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 border border-emerald-200">
          Inference Engine: Active
        </span>
      </PageHead>

      <div className="grid grid-cols-3 gap-4">
        <Stat label="Total Registered Models" value={models.length} color="border-l-steel" />
        <Stat label="Deployed in Production" value={deployedCount} color="border-l-emerald-600" />
        <Stat label="In Staging / Testing" value={testingCount} color="border-l-survey" />
      </div>

      <Card
        title="Model Registry & Benchmark Evaluation"
        className="mt-4"
        right={
          <div className="flex gap-1">
            {['all', 'deployed', 'testing'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`rounded px-3 py-1 text-xs font-medium capitalize ${
                  activeTab === tab ? 'bg-steel text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th>Model Architecture</th>
                <th>Task Type</th>
                <th>Version</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((m) => (
                <tr key={m.id} className="border-t">
                  <td>
                    <div className="font-semibold text-ink">{m.name}</div>
                    <div className="text-xs text-slate-500">{m.architecture} · {m.dataset}</div>
                  </td>
                  <td className="text-sm">{m.type}</td>
                  <td className="font-mono text-xs">{m.version}</td>
                  <td className="font-medium text-emerald-700">{m.precision}</td>
                  <td className="font-medium text-emerald-700">{m.recall}</td>
                  <td className="font-bold text-emerald-800">{m.f1}</td>
                  <td>
                    <Badge
                      cls={
                        m.status === 'Deployed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }
                    >
                      {m.status}
                    </Badge>
                  </td>
                  <td>
                    <button
                      onClick={() => toggleStatus(m.id)}
                      className={`rounded px-2.5 py-1 text-xs font-medium ${
                        m.status === 'Deployed'
                          ? 'border border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
                          : 'bg-steel text-white hover:bg-ink'
                      }`}
                    >
                      {m.status === 'Deployed' ? 'Demote to Testing' : 'Deploy to Prod'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Segmentation Pipeline Architecture">
          <div className="space-y-2 text-sm text-slate-700">
            <p>
              <b>Hybrid Architecture:</b> Ultralytics YOLO11n-seg provides bounding box localization and fast polygon segmentation, refined by UNet-ResNet34 for fine hairline cracks.
            </p>
            <p>
              <b>Pre-processing:</b> Adaptive histogram equalization (CLAHE) + Gaussian bilateral filtering to enhance surface contrast under uneven natural daylight.
            </p>
            <p>
              <b>Calibration:</b> Automated scale estimation calculates crack length (cm), average width (mm), and surface damage area (cm²).
            </p>
          </div>
        </Card>

        <Card title="Training & Validation Data Sources">
          <div className="space-y-2 text-sm text-slate-700">
            <div className="flex items-start gap-2">
              <Database className="mt-0.5 h-4 w-4 shrink-0 text-steel" />
              <div>
                <b>Crack500:</b> 500 high-resolution pavement and concrete bridge images with pixel-level ground truth masks.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Layers className="mt-0.5 h-4 w-4 shrink-0 text-steel" />
              <div>
                <b>SDNET2018:</b> Over 56,000 structural concrete images across bridge decks, walls, and pavements for defect classification.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Activity className="mt-0.5 h-4 w-4 shrink-0 text-steel" />
              <div>
                <b>Continuous Retraining:</b> Feedback from qualified civil engineers flags edge cases for next model checkpoint fine-tuning.
              </div>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
