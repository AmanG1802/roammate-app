import SwiftUI

struct CreateTripView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var tripStore: TripStore
    let onCreated: () -> Void

    @State private var name = ""
    @State private var startDate = Date()
    @State private var timezoneId: String = TimeZone.current.identifier
    @State private var isLoading = false
    @State private var error: String?
    @FocusState private var nameFieldFocused: Bool

    private static let knownTimezones: [String] = TimeZone.knownTimeZoneIdentifiers.sorted()

    var body: some View {
        NavigationStack {
            ZStack {
                Color.roammateBackground.ignoresSafeArea()

                VStack(spacing: RoammateSpacing.lg) {
                    Spacer().frame(height: RoammateSpacing.xl)

                    // Trip name input
                    VStack(spacing: 8) {
                        Text("What's this trip called?")
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                            .foregroundStyle(Color.roammateMuted)

                        TextField("e.g. Tokyo 2026", text: $name)
                            .font(.system(.title2, design: .rounded, weight: .bold))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(Color.roammateInk)
                            .focused($nameFieldFocused)

                        Rectangle()
                            .fill(Color.roammateIndigo.opacity(nameFieldFocused ? 1 : 0.3))
                            .frame(height: 2)
                            .frame(maxWidth: 200)
                            .animation(.easeInOut(duration: 0.2), value: nameFieldFocused)
                    }
                    .padding(.horizontal, RoammateSpacing.xl)

                    // Start date picker
                    VStack(spacing: 8) {
                        Text("When does it start?")
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                            .foregroundStyle(Color.roammateMuted)

                        DatePicker("", selection: $startDate, displayedComponents: .date)
                            .datePickerStyle(.compact)
                            .labelsHidden()
                    }

                    // Timezone picker — defaults to device tz, override for cross-tz trips
                    VStack(spacing: 8) {
                        Text("Trip timezone")
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                            .foregroundStyle(Color.roammateMuted)

                        Picker("Trip timezone", selection: $timezoneId) {
                            ForEach(Self.knownTimezones, id: \.self) { tz in
                                Text(tz).tag(tz)
                            }
                        }
                        .pickerStyle(.menu)
                        .tint(Color.roammateIndigo)
                    }

                    if let error {
                        Text(error)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.roammateDanger)
                            .padding(.horizontal, RoammateSpacing.md)
                    }

                    Spacer()

                    Button {
                        Task { await create() }
                    } label: {
                        if isLoading {
                            ProgressView().tint(.white)
                        } else {
                            HStack(spacing: 8) {
                                Image(systemName: "plus.circle.fill")
                                Text("Create Trip")
                            }
                        }
                    }
                    .buttonStyle(RoammatePrimaryButtonStyle(isLoading: isLoading))
                    .disabled(isLoading || name.trimmingCharacters(in: .whitespaces).isEmpty)
                    .padding(.horizontal, RoammateSpacing.md)
                    .padding(.bottom, RoammateSpacing.lg)
                }
            }
            .navigationTitle("New Trip")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .foregroundStyle(Color.roammateMuted)
                }
            }
            .onAppear { nameFieldFocused = true }
        }
    }

    private func create() async {
        isLoading = true
        defer { isLoading = false }
        let payload = TripCreate(
            name: name.trimmingCharacters(in: .whitespaces),
            startDate: startDate,
            endDate: nil,
            timezone: timezoneId
        )
        let result = await tripStore.create(payload)
        if result != nil {
            HapticManager.success()
            onCreated()
            dismiss()
        } else if let storeError = tripStore.error {
            HapticManager.error()
            self.error = storeError
        } else {
            HapticManager.success()
            onCreated()
            dismiss()
        }
    }
}
